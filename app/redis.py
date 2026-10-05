import logging
import time
from typing import Optional, Any
import redis
from app.config import settings

logger = logging.getLogger("shortx.redis")


class InMemoryFallbackRedis:
    """
    In-memory fallback cache conforming to Redis key-value & string operations.
    Used when a live Redis server is unavailable in the environment.
    """
    def __init__(self):
        self._store = {}
        self._expires = {}
        logger.warning("Using InMemoryFallbackRedis (Redis server unreachable or disabled).")

    def _purge_expired(self, key: str) -> bool:
        if key in self._expires:
            if time.time() > self._expires[key]:
                self._store.pop(key, None)
                self._expires.pop(key, None)
                return True
        return False

    def get(self, key: str) -> Optional[str]:
        if self._purge_expired(key):
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = str(value)
        if ex is not None:
            self._expires[key] = time.time() + ex
        else:
            self._expires.pop(key, None)
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                self._expires.pop(k, None)
                count += 1
        return count

    def incr(self, key: str, amount: int = 1) -> int:
        self._purge_expired(key)
        val = int(self._store.get(key, 0)) + amount
        self._store[key] = str(val)
        return val

    def expire(self, key: str, seconds: int) -> bool:
        if key in self._store:
            self._expires[key] = time.time() + seconds
            return True
        return False

    def ping(self) -> bool:
        return True

    def flushdb(self) -> bool:
        self._store.clear()
        self._expires.clear()
        return True


_redis_client: Optional[Any] = None


def get_redis_client() -> Any:
    """
    Returns an active Redis client or in-memory fallback if Redis is down.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=1.5
        )
        client.ping()
        _redis_client = client
        logger.info("Successfully connected to Redis at %s", settings.REDIS_URL)
        return _redis_client
    except Exception as e:
        logger.warning(
            "Could not connect to Redis at %s (%s). Falling back to InMemoryFallbackRedis.",
            settings.REDIS_URL,
            str(e)
        )
        _redis_client = InMemoryFallbackRedis()
        return _redis_client


def reset_redis_client(client: Optional[Any] = None):
    """Allows injecting custom/fake redis in test suites."""
    global _redis_client
    _redis_client = client
