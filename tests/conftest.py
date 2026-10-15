import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models

# Xotiradagi vaqtinchalik SQLite bazasi
SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 1. Har bir test uchun toza baza yaratish va o'chirish
@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# 2. TestClient — haqiqiy bazani test bazasiga almashtiradi
@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# 3. Tayyor test foydalanuvchisi yaratish
@pytest.fixture()
def test_user(client):
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201
    new_user = response.json()
    new_user["password"] = "password123"
    return new_user


# 4. Foydalanuvchi uchun JWT Token olish
@pytest.fixture()
def token(test_user, client):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# 5. Tokeni ulangan (avtorizatsiyadan o'tgan) mijoz
@pytest.fixture()
def authorized_client(client, token):
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# 6. Test uchun 3 ta tayyor post yaratish
# ─── FIXTURE: Test Posts ──────────────────────
@pytest.fixture()
def test_posts(test_user, db):
    posts_data = [
        {
            "title": "Birinchi post",
            "body": "Birinchi matn",  # <-- "content" o'rniga "body"
            "published": True,
            "owner_id": test_user["id"],
        },
        {
            "title": "Ikkinchi post",
            "body": "Ikkinchi matn",  # <-- "content" o'rniga "body"
            "published": True,
            "owner_id": test_user["id"],
        },
        {
            "title": "Uchinchi post",
            "body": "Uchinchi matn",  # <-- "content" o'rniga "body"
            "published": False,
            "owner_id": test_user["id"],
        },
    ]
    posts = [models.Post(**p) for p in posts_data]
    db.add_all(posts)
    db.commit()
    return db.query(models.Post).all()