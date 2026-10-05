import time
import logging
from typing import Tuple
from fastapi import Request, HTTPException, status
from app.redis import get_redis_client
from app.config import settings

logger = logging.getLogger("shortx.ratelimit")


class RateLimitService:
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Extracts client IP address, respecting X-Forwarded-For if behind reverse proxy."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in list is original client
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    @classmethod
    def is_rate_limited(
        cls,
        key_identifier: str,
        limit: int = settings.RATE_LIMIT_REQUESTS,
        window: int = settings.RATE_LIMIT_WINDOW_SECONDS
    ) -> Tuple[bool, int, int]:
        """
        Fixed-window rate limiter using Redis INCR with EXPIRE.
        Returns: (is_limited, current_requests, retry_after_seconds)
        """
        try:
            client = get_redis_client()
            current_window = int(time.time() // window)
            redis_key = f"rate_limit:{key_identifier}:{current_window}"

            current_count = client.incr(redis_key)
            if current_count == 1:
                # Set TTL on new window key
                client.expire(redis_key, window + 1)

            # Seconds remaining in this window
            now = time.time()
            retry_after = int(((current_window + 1) * window) - now)
            if retry_after <= 0:
                retry_after = 1

            if current_count > limit:
                logger.warning(
                    "Rate limit exceeded for %s: %d/%d requests (retry in %ds)",
                    key_identifier, current_count, limit, retry_after
                )
                return True, current_count, retry_after

            return False, current_count, retry_after
        except Exception as e:
            logger.warning("Error checking rate limit in Redis: %s. Allowing request.", str(e))
            # Graceful degradation: allow request if rate limit store fails
            return False, 1, 0


def rate_limiter_dependency(
    limit: int = settings.RATE_LIMIT_REQUESTS,
    window: int = settings.RATE_LIMIT_WINDOW_SECONDS
):
    """
    FastAPI dependency factory for rate limiting.
    Usage: Depends(rate_limiter_dependency(100, 60))
    """
    async def dependency(request: Request):
        client_ip = RateLimitService.get_client_ip(request)
        is_limited, count, retry_after = RateLimitService.is_rate_limited(
            client_ip, limit=limit, window=window
        )
        if is_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit} requests per {window}s). Please wait {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        return True

    return dependency
