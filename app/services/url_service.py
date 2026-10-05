import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.url import URL
from app.models.click import Click
from app.schemas.url import DashboardStats
from app.schemas.analytics import URLAnalyticsResponse, ClickTimelinePoint
from app.services.cache_service import CacheService
from app.config import settings

BASE62_ALPHABET = string.ascii_letters + string.digits


class URLService:
    @staticmethod
    def generate_random_code(length: int = settings.SHORT_CODE_LENGTH) -> str:
        """Generates a secure random base62 string."""
        return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))

    @classmethod
    def generate_unique_code(cls, db: Session, length: int = settings.SHORT_CODE_LENGTH, max_attempts: int = 10) -> str:
        """Generates a unique short code with collision handling."""
        for _ in range(max_attempts):
            code = cls.generate_random_code(length)
            exists = db.query(URL.id).filter(URL.short_code == code).first()
            if not exists:
                return code
        # In the unlikely event of collisions, increase length by 1
        return cls.generate_random_code(length + 1)

    @classmethod
    def create_short_url(
        cls,
        db: Session,
        original_url: str,
        user_id: Optional[int] = None
    ) -> URL:
        short_code = cls.generate_unique_code(db)
        url_obj = URL(
            user_id=user_id,
            original_url=original_url,
            short_code=short_code,
            click_count=0
        )
        db.add(url_obj)
        db.commit()
        db.refresh(url_obj)

        # Pre-warm Redis cache for instant first-hit redirect
        CacheService.set_url(short_code, original_url)
        return url_obj

    @staticmethod
    def get_by_short_code(db: Session, short_code: str) -> Optional[URL]:
        return db.query(URL).filter(URL.short_code == short_code).first()

    @staticmethod
    def get_by_id(db: Session, url_id: int) -> Optional[URL]:
        return db.query(URL).filter(URL.id == url_id).first()

    @staticmethod
    def list_user_urls(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[URL]:
        return (
            db.query(URL)
            .filter(URL.user_id == user_id)
            .order_by(URL.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def delete_url(cls, db: Session, url_id: int, user_id: int) -> bool:
        url_obj = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()
        if not url_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="URL not found or unauthorized"
            )

        short_code = url_obj.short_code
        db.delete(url_obj)
        db.commit()

        # Invalidate Redis cache entry
        CacheService.delete_url(short_code)
        return True

    @staticmethod
    def record_click(
        db: Session,
        url_obj: URL,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Increments URL click count and logs a Click event for analytics.
        """
        try:
            url_obj.click_count += 1
            click_record = Click(
                url_id=url_obj.id,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None
            )
            db.add(click_record)
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def get_dashboard_stats(db: Session, user_id: int) -> DashboardStats:
        total_links = db.query(func.count(URL.id)).filter(URL.user_id == user_id).scalar() or 0
        total_clicks = (
            db.query(func.sum(URL.click_count)).filter(URL.user_id == user_id).scalar() or 0
        )
        now = datetime.now(timezone.utc)
        active_links = (
            db.query(func.count(URL.id))
            .filter(
                URL.user_id == user_id,
                (URL.expires_at == None) | (URL.expires_at > now)
            )
            .scalar() or 0
        )

        return DashboardStats(
            total_links=total_links,
            total_clicks=total_clicks,
            active_links=active_links
        )

    @staticmethod
    def get_url_analytics(db: Session, url_id: int, user_id: int) -> URLAnalyticsResponse:
        url_obj = db.query(URL).filter(URL.id == url_id, URL.user_id == user_id).first()
        if not url_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="URL not found or unauthorized"
            )

        # Get latest click
        last_click = (
            db.query(Click.clicked_at)
            .filter(Click.url_id == url_id)
            .order_by(Click.clicked_at.desc())
            .first()
        )
        last_click_at = last_click[0] if last_click else None

        # Build 7-day click timeline (grouped by date)
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=6)

        clicks = (
            db.query(Click.clicked_at)
            .filter(Click.url_id == url_id, Click.clicked_at >= start_date)
            .all()
        )

        # Group into daily buckets
        daily_counts: Dict[str, int] = {}
        for i in range(7):
            d = (start_date + timedelta(days=i)).strftime("%b %d")
            daily_counts[d] = 0

        for c in clicks:
            d_str = c[0].strftime("%b %d")
            if d_str in daily_counts:
                daily_counts[d_str] += 1

        timeline = [ClickTimelinePoint(date=k, clicks=v) for k, v in daily_counts.items()]

        short_url = f"{settings.BASE_URL}/{url_obj.short_code}"

        return URLAnalyticsResponse(
            id=url_obj.id,
            short_code=url_obj.short_code,
            short_url=short_url,
            original_url=url_obj.original_url,
            total_clicks=url_obj.click_count,
            created_at=url_obj.created_at,
            last_click_at=last_click_at,
            clicks_timeline=timeline
        )
