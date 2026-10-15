import pytest


def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "username": "ali",
            "email": "ali@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ali@example.com"
    assert data["username"] == "ali"
    assert "password" not in data
    assert "id" in data


def test_create_user_duplicate_email(client):
    user_data = {
        "username": "ali",
        "email": "ali@example.com",
        "password": "password123"
    }
    client.post("/users/", json=user_data)
    
    # Ikkinchi marta xuddi shu email bilan yuborish
    response = client.post(
        "/users/",
        json={
            "username": "vali",
            "email": "ali@example.com",
            "password": "password456"
        }
    )
    assert response.status_code == 400


def test_create_user_invalid_email(client):
    response = client.post(
        "/users/",
        json={
            "username": "ali",
            "email": "not-an-email",
            "password": "password123"
        }
    )
    assert response.status_code == 422


def test_get_user(client, test_user):
    response = client.get(f"/users/{test_user['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]


def test_get_user_not_found(client):
    response = client.get("/users/99999")
    assert response.status_code == 404