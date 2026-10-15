import pytest
from jose import jwt
from app.config import settings


def test_login(client, test_user):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_token_valid(client, test_user):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    token = response.json()["access_token"]
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.algorithm]
    )
    assert payload.get("user_id") == test_user["id"]


def test_login_wrong_password(client, test_user):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 403


def test_login_wrong_email(client):
    response = client.post(
        "/login",
        data={
            "username": "nobody@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 403