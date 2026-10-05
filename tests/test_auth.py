import pytest


def test_signup_success(client):
    response = client.post(
        "/auth/signup",
        json={"email": "newuser@example.com", "password": "securepassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"


def test_signup_duplicate_email(client):
    client.post(
        "/auth/signup",
        json={"email": "dup@example.com", "password": "password123"}
    )
    response = client.post(
        "/auth/signup",
        json={"email": "dup@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success(client):
    client.post(
        "/auth/signup",
        json={"email": "loginuser@example.com", "password": "mypassword"}
    )
    response = client.post(
        "/auth/login",
        json={"email": "loginuser@example.com", "password": "mypassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginuser@example.com"


def test_login_wrong_password(client):
    client.post(
        "/auth/signup",
        json={"email": "wrongpass@example.com", "password": "correctpassword"}
    )
    response = client.post(
        "/auth/login",
        json={"email": "wrongpass@example.com", "password": "badpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_current_user_me(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "tester@shortx.io"


def test_get_current_user_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
