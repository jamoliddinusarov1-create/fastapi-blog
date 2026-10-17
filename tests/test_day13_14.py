import io
import json
import pytest
from starlette.websockets import WebSocketDisconnect
from app import models


def test_simple_websocket(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Salom FastAPI")
        data = websocket.receive_text()
        assert data == "Siz yubordingiz: Salom FastAPI"


def test_public_chat_websocket(client):
    with client.websocket_connect("/ws/chat/lobby/Ali") as ws:
        join_msg = ws.receive_json()
        assert join_msg["type"] == "system"
        assert "Ali" in join_msg["message"]

        ws.send_text("Salom barchaga!")
        msg = ws.receive_json()
        assert msg["type"] == "message"
        assert msg["username"] == "Ali"
        assert msg["message"] == "Salom barchaga!"


def test_secure_chat_without_token(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/chat/secret"):
            pass
    assert exc.value.code == 1008


def test_secure_chat_with_token(client, token, test_user):
    with client.websocket_connect(f"/ws/chat/secret?token={token}") as ws:
        join_msg = ws.receive_json()
        assert join_msg["type"] == "system"
        assert test_user["username"] in join_msg["message"]

        # Yozmoqda bildirishnomasi
        ws.send_json({"type": "typing", "is_typing": True})

        # Oddiy xabar
        ws.send_text("Maxfiy xabar")
        msg = ws.receive_json()
        assert msg["type"] == "message"
        assert msg["message"] == "Maxfiy xabar"


def test_dm_websocket(client, token, test_user, db):
    # Ikkinchi user yaratamiz
    second_user = models.User(
        username="vali",
        email="vali@example.com",
        password="secretpassword",
        is_active=True
    )
    db.add(second_user)
    db.commit()
    db.refresh(second_user)

    with client.websocket_connect(f"/ws/dm/{second_user.id}?token={token}") as ws:
        join_msg = ws.receive_json()
        assert join_msg["type"] == "system"
        assert "DM" in join_msg["message"]

        ws.send_text("Salom Vali, bu xususiy xabar")
        msg = ws.receive_json()
        assert msg["type"] == "message"
        assert msg["message"] == "Salom Vali, bu xususiy xabar"


def test_ws_rooms_and_history(client, test_user, token, db):
    # Tarix tekshirish uchun xabar qo'shamiz
    test_msg = models.Message(room="history_room", username="testuser", content="Salom tarix!")
    db.add(test_msg)
    db.commit()

    res = client.get("/ws/rooms/history_room/history")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[-1]["content"] == "Salom tarix!"


def test_ws_online_endpoint(client):
    res = client.get("/ws/online")
    assert res.status_code == 200
    assert "online_users" in res.json()
    assert "count" in res.json()


def test_upload_image(authorized_client):
    file_content = b"fake-image-bytes"
    file = io.BytesIO(file_content)
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("test.png", file, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith(".png")
    assert data["url"].startswith("/uploads/")
    assert data["size"] == len(file_content)


def test_upload_avatar(authorized_client):
    file_content = b"avatar-image-data"
    file = io.BytesIO(file_content)
    response = authorized_client.post(
        "/upload/avatar",
        files={"file": ("avatar.jpg", file, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"].startswith("/uploads/")


def test_upload_pdf_file(authorized_client):
    pdf_content = b"%PDF-1.4 test pdf content"
    file = io.BytesIO(pdf_content)
    response = authorized_client.post(
        "/upload/file",
        files={"file": ("document.pdf", file, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith(".pdf")
    assert data["content_type"] == "application/pdf"


def test_upload_invalid_type(authorized_client):
    file = io.BytesIO(b"malicious script")
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("virus.exe", file, "application/x-msdownload")}
    )
    assert response.status_code == 400
