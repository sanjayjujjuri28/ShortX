import pytest
from app.services.cache_service import CacheService
from app.redis import get_redis_client


def test_cache_hit_and_miss(client, auth_headers):
    # Cache miss initially
    assert CacheService.get_url("unknownCode123") is None

    # Create a URL which pre-warms the cache
    create_res = client.post(
        "/urls",
        json={"original_url": "https://redis.io/commands"},
        headers=auth_headers
    )
    code = create_res.json()["short_code"]

    # Verify cached value exists
    cached = CacheService.get_url(code)
    assert cached == "https://redis.io/commands"

    # Invalidate cache
    client.delete(f"/urls/{create_res.json()['id']}", headers=auth_headers)
    assert CacheService.get_url(code) is None


def test_redirect_populates_cache_on_miss(client, auth_headers):
    # Create URL
    create_res = client.post(
        "/urls",
        json={"original_url": "https://postgresql.org"},
        headers=auth_headers
    )
    code = create_res.json()["short_code"]

    # Explicitly clear Redis cache to simulate cache eviction
    get_redis_client().flushdb()
    assert CacheService.get_url(code) is None

    # Request redirect (Cache Miss -> DB Fetch -> Cache Store -> Redirect)
    res = client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "https://postgresql.org"

    # Redis should now have the key cached!
    assert CacheService.get_url(code) == "https://postgresql.org"
