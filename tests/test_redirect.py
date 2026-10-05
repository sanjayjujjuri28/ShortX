import pytest


def test_redirect_to_original_url(client, auth_headers):
    create_res = client.post(
        "/urls",
        json={"original_url": "https://docs.python.org/3/"},
        headers=auth_headers
    )
    short_code = create_res.json()["short_code"]
    url_id = create_res.json()["id"]

    # Request redirect (do not follow redirects to inspect 307 header)
    redirect_res = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_res.status_code == 307
    assert redirect_res.headers["location"] == "https://docs.python.org/3/"


def test_redirect_nonexistent_returns_404(client):
    response = client.get("/nonExistent999", follow_redirects=False)
    assert response.status_code == 404


def test_url_analytics(client, auth_headers):
    create_res = client.post(
        "/urls",
        json={"original_url": "https://fastapi.tiangolo.com"},
        headers=auth_headers
    )
    url_id = create_res.json()["id"]
    short_code = create_res.json()["short_code"]

    # Trigger clicks
    client.get(f"/{short_code}", follow_redirects=False)
    client.get(f"/{short_code}", follow_redirects=False)

    # Get analytics
    analytics_res = client.get(f"/urls/{url_id}/analytics", headers=auth_headers)
    assert analytics_res.status_code == 200
    data = analytics_res.json()
    assert data["id"] == url_id
    assert data["short_code"] == short_code
    assert data["total_clicks"] >= 2
    assert "clicks_timeline" in data
    assert len(data["clicks_timeline"]) == 7
