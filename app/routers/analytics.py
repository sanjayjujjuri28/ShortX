from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import URLAnalyticsResponse
from app.services.url_service import URLService
from app.security import get_current_user

router = APIRouter(prefix="/urls", tags=["Analytics"])


@router.get("/{url_id}/analytics", response_model=URLAnalyticsResponse)
def get_url_analytics(
    url_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns analytics metrics and 7-day click trend for a specific URL.
    """
    analytics = URLService.get_url_analytics(db=db, url_id=url_id, user_id=current_user.id)
    # Adjust base URL if request host is provided
    if request:
        base = str(request.base_url).rstrip("/")
        analytics.short_url = f"{base}/{analytics.short_code}"
    return analytics
