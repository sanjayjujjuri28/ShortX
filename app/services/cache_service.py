import logging
from typing import Optional
from app.redis import get_redis_client
from app.config import settings

logger = logging.getLogger("shortx.cache")


class CacheService:
    @staticmethod
    def _make_key(short_code: str) -> str:
        return f"url:{short_code}"

    @classmethod
    def get_url(cls, short_code: str) -> Optional[str]:
        """
        Retrieves original URL from Redis cache.
        Returns None if cache miss or Redis error.
        """
        try:
            client = get_redis_client()
            val = client.get(cls._make_key(short_code))
            if val:
                logger.info("Redis CACHE HIT for code: %s", short_code)
                return val
            logger.info("Redis CACHE MISS for code: %s", short_code)
            return None
        except Exception as e:
            logger.warning("Error reading from Redis cache: %s", str(e))
            return None

    @classmethod
    def set_url(cls, short_code: str, original_url: str, ttl: Optional[int] = None) -> bool:
        """
        Stores short_code -> original_url mapping in Redis with TTL.
        """
        try:
            client = get_redis_client()
            ttl = ttl or settings.REDIS_CACHE_TTL
            client.set(cls._make_key(short_code), original_url, ex=ttl)
            logger.info("Redis CACHE STORED for code: %s (TTL: %ds)", short_code, ttl)
            return True
        except Exception as e:
            logger.warning("Error writing to Redis cache: %s", str(e))
            return False

    @classmethod
    def delete_url(cls, short_code: str) -> bool:
        """
        Invalidates cached short code upon URL deletion.
        """
        try:
            client = get_redis_client()
            client.delete(cls._make_key(short_code))
            logger.info("Redis CACHE INVALIDATED for code: %s", short_code)
            return True
        except Exception as e:
            logger.warning("Error invalidating Redis cache: %s", str(e))
            return False
