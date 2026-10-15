import pytest


def test_get_all_posts(client, test_posts):
    response = client.get("/posts/")
    assert response.status_code == 200
    assert len(response.json()) == len(test_posts)


def test_get_post(client, test_posts):
    response = client.get(f"/posts/{test_posts[0].id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_posts[0].id
    assert data["title"] == test_posts[0].title
    assert data["body"] == test_posts[0].body  # <-- "body" bo'ldi


def test_get_post_not_found(client):
    response = client.get("/posts/99999")
    assert response.status_code == 404


def test_create_post(authorized_client):
    response = authorized_client.post(
        "/posts/",
        json={
            "title": "Yangi post",
            "body": "Yangi kontent matni",  # <-- "content" o'rniga "body"
            "published": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Yangi post"
    assert data["body"] == "Yangi kontent matni"  # <-- "body"
    assert data["published"] is True
    assert "id" in data
    assert "owner_id" in data


def test_create_post_unauthorized(client):
    response = client.post(
        "/posts/",
        json={
            "title": "Post",
            "body": "Kontent matni",  # <-- "body"
        },
    )
    assert response.status_code == 401


def test_update_post(authorized_client, test_posts):
    response = authorized_client.put(
        f"/posts/{test_posts[0].id}",
        json={
            "title": "Yangilangan sarlavha",
            "body": "Yangilangan matn",  # <-- "body"
            "published": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Yangilangan sarlavha"
    assert data["body"] == "Yangilangan matn"  # <-- "body"


def test_delete_post(authorized_client, test_posts):
    # ID ni oldindan oddiy o'zgaruvchiga olib qo'yamiz:
    post_id = test_posts[0].id

    # 1. Postni o'chiramiz
    response = authorized_client.delete(f"/posts/{post_id}")
    assert response.status_code == 204

    # 2. Endi obyektga emas, o'sha saqlangan ID ga so'rov yuboramiz
    response_check = authorized_client.get(f"/posts/{post_id}")
    assert response_check.status_code == 404