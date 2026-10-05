import pytest


def test_create_short_url(client, auth_headers):
    response = client.post(
        "/urls",
        json={"original_url": "https://github.com/fastapi/fastapi"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://github.com/fastapi/fastapi"
    assert len(data["short_code"]) >= 6
    assert data["short_code"] in data["short_url"]
    assert data["click_count"] == 0


def test_create_url_normalizes_protocol(client, auth_headers):
    response = client.post(
        "/urls",
        json={"original_url": "youtube.com/watch?v=dQw4w9WgXcQ"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["original_url"] == "https://youtube.com/watch?v=dQw4w9WgXcQ"


def test_list_urls(client, auth_headers):
    client.post("/urls", json={"original_url": "https://python.org"}, headers=auth_headers)
    client.post("/urls", json={"original_url": "https://redis.io"}, headers=auth_headers)

    response = client.get("/urls", headers=auth_headers)
    assert response.status_code == 200
    urls = response.json()
    assert len(urls) >= 2
    assert any(u["original_url"] == "https://python.org" for u in urls)
    assert any(u["original_url"] == "https://redis.io" for u in urls)


def test_get_dashboard_stats(client, auth_headers):
    client.post("/urls", json={"original_url": "https://news.ycombinator.com"}, headers=auth_headers)

    response = client.get("/urls/stats", headers=auth_headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_links"] >= 1
    assert "total_clicks" in stats
    assert "active_links" in stats


def test_delete_url(client, auth_headers):
    create_res = client.post(
        "/urls",
        json={"original_url": "https://wikipedia.org"},
        headers=auth_headers
    )
    url_id = create_res.json()["id"]

    del_res = client.delete(f"/urls/{url_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # Should 404 on subsequent get
    get_res = client.get(f"/urls/{url_id}", headers=auth_headers)
    assert get_res.status_code == 404
