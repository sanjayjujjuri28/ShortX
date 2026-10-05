from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.url import URL
from app.schemas.url import URLCreate, URLResponse, DashboardStats
from app.services.url_service import URLService
from app.security import get_current_user
from app.services.rate_limit_service import rate_limiter_dependency
from app.config import settings

router = APIRouter(prefix="/urls", tags=["URLs"])


def to_response(url_obj: URL, request: Request) -> URLResponse:
    base = str(request.base_url).rstrip("/") if request else settings.BASE_URL
    return URLResponse(
        id=url_obj.id,
        original_url=url_obj.original_url,
        short_code=url_obj.short_code,
        short_url=f"{base}/{url_obj.short_code}",
        click_count=url_obj.click_count,
        created_at=url_obj.created_at,
        expires_at=url_obj.expires_at
    )


@router.post(
    "",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter_dependency(limit=settings.RATE_LIMIT_REQUESTS, window=settings.RATE_LIMIT_WINDOW_SECONDS))]
)
def create_url(
    payload: URLCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new shortened URL for the authenticated user."""
    url_obj = URLService.create_short_url(
        db=db,
        original_url=payload.original_url,
        user_id=current_user.id
    )
    return to_response(url_obj, request)


@router.get("", response_model=List[URLResponse])
def get_user_urls(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all short URLs created by the authenticated user."""
    urls = URLService.list_user_urls(db=db, user_id=current_user.id, skip=skip, limit=limit)
    return [to_response(u, request) for u in urls]


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns aggregated dashboard statistics for the authenticated user."""
    return URLService.get_dashboard_stats(db=db, user_id=current_user.id)


@router.get("/{url_id}", response_model=URLResponse)
def get_url_details(
    url_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves details of a single URL."""
    url_obj = URLService.get_by_id(db=db, url_id=url_id)
    if not url_obj or url_obj.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    return to_response(url_obj, request)


@router.delete("/{url_id}", status_code=status.HTTP_200_OK)
def delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a short URL and invalidates its Redis cache entry."""
    URLService.delete_url(db=db, url_id=url_id, user_id=current_user.id)
    return {"detail": "URL deleted successfully"}
