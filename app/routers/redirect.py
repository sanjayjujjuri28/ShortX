import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache_service import CacheService
from app.services.url_service import URLService
from app.services.rate_limit_service import RateLimitService, rate_limiter_dependency
from app.config import settings

logger = logging.getLogger("shortx.redirect")

router = APIRouter(tags=["Redirect"])


@router.api_route(
    "/{short_code}",
    methods=["GET", "HEAD"],
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    dependencies=[Depends(rate_limiter_dependency(limit=settings.RATE_LIMIT_REQUESTS, window=settings.RATE_LIMIT_WINDOW_SECONDS))]
)
def redirect_to_url(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirects short URL to original destination.
    Implements Redis Cache Hit / Miss pattern followed by analytics click logging.
    """
    # Exclude reserved words and static assets
    reserved = {"docs", "redoc", "openapi.json", "api", "auth", "urls", "static", "favicon.ico"}
    if short_code.lower() in reserved or "." in short_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    client_ip = RateLimitService.get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # Step 1: Check Redis Cache (Hit)
    cached_url = CacheService.get_url(short_code)

    # Step 2: Fetch and record click event
    url_obj = URLService.get_by_short_code(db, short_code)
    if url_obj:
        URLService.record_click(db, url_obj, ip_address=client_ip, user_agent=user_agent)

    if cached_url:
        return RedirectResponse(url=cached_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # Step 3: Cache Miss -> Fallback to PostgreSQL/Database
    if not url_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short link '{short_code}' not found"
        )

    # Step 4: Populate Redis cache for subsequent visits
    CacheService.set_url(short_code, url_obj.original_url)

    # Step 5: Redirect to target destination
    return RedirectResponse(url=url_obj.original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
