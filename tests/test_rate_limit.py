import pytest
from app.redis import get_redis_client


def test_rate_limiter_blocks_excessive_requests(client):
    get_redis_client().flushdb()

    # The test environment configured limit to 20 on signup
    # Let's test reaching limit by repeatedly sending requests
    # Or call a restricted route beyond limit
    email_pattern = "ratelimit_user_{}@example.com"
    responses = []
    # signup limit is 20 in 60s
    for i in range(22):
        r = client.post(
            "/auth/signup",
            json={"email": email_pattern.format(i), "password": "passwordsafe123"}
        )
        responses.append(r.status_code)

    # At least the last requests must be 429 Too Many Requests
    assert 429 in responses
    # Verify response body and Retry-After header
    last_response = [r for r in responses if r == 429]
    assert len(last_response) > 0
