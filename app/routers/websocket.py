import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

MAX_MESSAGE_LENGTH = 2000


def _get_user_from_token(token: str, db: Session) -> Optional[models.User]:
    """Token orqali foydalanuvchini bazadan qidirib topish"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user and user.is_active:
        return user
    return None


def _save_message(db: Session, room: str, username: str, content: str):
    """Xabarni bazaga saqlash"""
    try:
        msg = models.Message(room=room, username=username, content=content)
        db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Xabarni saqlashda xatolik: {e}")


# ─── CONNECTION MANAGER ───────────────────────
class ConnectionManager:
    def __init__(self):
        # {room_name: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # {websocket: username} — online foydalanuvchilarni kuzatish uchun
        self.socket_users: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, room: str, username: Optional[str] = None):
        await websocket.accept()
        self.active_connections.setdefault(room, []).append(websocket)
        if username:
            self.socket_users[websocket] = username
        logger.info(f"Yangi ulanish: {room} | Jami: {len(self.active_connections[room])}")

    def disconnect(self, websocket: WebSocket, room: str):
        conns = self.active_connections.get(room)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                del self.active_connections[room]
        self.socket_users.pop(websocket, None)
        logger.info(f"Uzildi: {room}")

    async def send_personal(self, message: str, websocket: WebSocket):
        """Faqat bitta clientga yuborish"""
        await websocket.send_text(message)

    async def broadcast(self, message: str, room: str):
        """Xonadagi barcha clientlarga yuborish"""
        for conn in list(self.active_connections.get(room, [])):
            try:
                await conn.send_text(message)
            except Exception:
                self.disconnect(conn, room)

    async def broadcast_except(self, message: str, room: str, exclude: WebSocket):
        """O'zidan boshqa barchaga yuborish"""
        for conn in list(self.active_connections.get(room, [])):
            if conn != exclude:
                try:
                    await conn.send_text(message)
                except Exception:
                    self.disconnect(conn, room)

    def get_room_count(self, room: str) -> int:
        """Xonadagi foydalanuvchilar soni"""
        return len(self.active_connections.get(room, []))

    def get_online_users(self) -> List[str]:
        """Barcha online foydalanuvchilar ro'yxati"""
        return sorted(list({u for u in self.socket_users.values() if u}))


manager = ConnectionManager()


# ─── 2-QISM: ODDIY WEBSOCKET ──────────────────
@router.websocket("/ws")
async def simple_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Keldi: {data}")
            await websocket.send_text(f"Siz yubordingiz: {data}")
    except WebSocketDisconnect:
        logger.info("Client uzildi (/ws)")


# ─── 3-QISM: CHAT (Ochiq xona) ────────────────
@router.websocket("/ws/chat/{room}/{username}")
async def public_chat_endpoint(
    websocket: WebSocket,
    room: str,
    username: str,
    db: Session = Depends(get_db),
):
    await manager.connect(websocket, room, username=username)

    # Kirish xabari
    join_message = json.dumps({
        "type": "system",
        "message": f"{username} xonaga kirdi!",
        "room": room,
        "users_count": manager.get_room_count(room),
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    await manager.broadcast(join_message, room)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = raw_data.strip()
            if not data:
                continue

            # Yozmoqda bildirishnomasi tekshiruvi (Amaliy mashq 1)
            is_typing = False
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and parsed.get("type") == "typing":
                    is_typing = True
                    typing_msg = json.dumps({
                        "type": "typing",
                        "username": username,
                        "room": room,
                        "is_typing": parsed.get("is_typing", True),
                    })
                    await manager.broadcast_except(typing_msg, room, exclude=websocket)
            except (json.JSONDecodeError, TypeError):
                pass

            if is_typing:
                continue

            # Oddiy xabar
            msg_text = data[:MAX_MESSAGE_LENGTH]
            await run_in_threadpool(_save_message, db, room, username, msg_text)

            message = json.dumps({
                "type": "message",
                "username": username,
                "message": msg_text,
                "room": room,
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            await manager.broadcast(message, room)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        leave_message = json.dumps({
            "type": "system",
            "message": f"{username} xonadan chiqdi",
            "room": room,
            "users_count": manager.get_room_count(room),
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        await manager.broadcast(leave_message, room)


# ─── 4-QISM: XAVFSIZ CHAT (JWT bilan) ─────────
@router.websocket("/ws/chat/{room}")
async def secure_chat_endpoint(
    websocket: WebSocket,
    room: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if not token:
        await websocket.close(code=1008)
        return

    user = await run_in_threadpool(_get_user_from_token, token, db)
    if not user:
        await websocket.close(code=1008)
        return

    username = user.username
    await manager.connect(websocket, room, username=username)

    join_message = json.dumps({
        "type": "system",
        "message": f"{username} joined",
        "room": room,
        "users_count": manager.get_room_count(room),
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    await manager.broadcast(join_message, room)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = raw_data.strip()
            if not data:
                continue

            # Yozmoqda tekshiruvi
            is_typing = False
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and parsed.get("type") == "typing":
                    is_typing = True
                    typing_msg = json.dumps({
                        "type": "typing",
                        "username": username,
                        "room": room,
                        "is_typing": parsed.get("is_typing", True),
                    })
                    await manager.broadcast_except(typing_msg, room, exclude=websocket)
            except (json.JSONDecodeError, TypeError):
                pass

            if is_typing:
                continue

            msg_text = data[:MAX_MESSAGE_LENGTH]
            await run_in_threadpool(_save_message, db, room, username, msg_text)

            message = json.dumps({
                "type": "message",
                "username": username,
                "message": msg_text,
                "room": room,
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            await manager.broadcast(message, room)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        leave_message = json.dumps({
            "type": "system",
            "message": f"{username} left",
            "room": room,
            "users_count": manager.get_room_count(room),
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        await manager.broadcast(leave_message, room)


# ─── UY VAZIFASI 1: XUSUSIY XABAR (DM) ────────
@router.websocket("/ws/dm/{target_user_id}")
async def direct_message(
    websocket: WebSocket,
    target_user_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    user = await run_in_threadpool(_get_user_from_token, token, db)
    if not user:
        await websocket.close(code=1008)
        return

    # Target foydalanuvchini tekshirish
    target = db.query(models.User).filter(models.User.id == target_user_id).first()
    if not target:
        await websocket.close(code=1008)
        return

    # Deterministic 1-on-1 xona nomi
    dm_room = f"dm_{min(user.id, target_user_id)}_{max(user.id, target_user_id)}"
    username = user.username
    await manager.connect(websocket, dm_room, username=username)

    join_msg = json.dumps({
        "type": "system",
        "message": f"{username} DM ulanishiga qo'shildi",
        "room": dm_room,
        "users_count": manager.get_room_count(dm_room),
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    await manager.broadcast(join_msg, dm_room)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = raw_data.strip()
            if not data:
                continue

            # Yozmoqda bildirishnomasi
            is_typing = False
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and parsed.get("type") == "typing":
                    is_typing = True
                    await manager.broadcast_except(
                        json.dumps({
                            "type": "typing",
                            "username": username,
                            "room": dm_room,
                            "is_typing": parsed.get("is_typing", True),
                        }),
                        dm_room,
                        exclude=websocket,
                    )
            except (json.JSONDecodeError, TypeError):
                pass

            if is_typing:
                continue

            msg_text = data[:MAX_MESSAGE_LENGTH]
            await run_in_threadpool(_save_message, db, dm_room, username, msg_text)

            dm_payload = json.dumps({
                "type": "message",
                "username": username,
                "message": msg_text,
                "room": dm_room,
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            await manager.broadcast(dm_payload, dm_room)

    except WebSocketDisconnect:
        manager.disconnect(websocket, dm_room)
        leave_msg = json.dumps({
            "type": "system",
            "message": f"{username} DM dan chiqdi",
            "room": dm_room,
            "users_count": manager.get_room_count(dm_room),
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        await manager.broadcast(leave_msg, dm_room)


# ─── ACTIVE ROOMS ─────────────────────────────
@router.get("/ws/rooms")
def get_active_rooms():
    return {
        "rooms": {room: len(conns) for room, conns in manager.active_connections.items()}
    }


# ─── UY VAZIFASI 2: ONLINE FOYDALANUVCHILAR ───
@router.get("/ws/online")
def get_online_users():
    online = manager.get_online_users()
    return {
        "online_users": online,
        "count": len(online),
    }


# ─── AMALIY MASHQ 2: XONA TARIXI ──────────────
@router.get("/ws/rooms/{room}/history", response_model=List[schemas.MessageResponse])
def get_room_history(
    room: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Message)
        .filter(models.Message.room == room)
        .order_by(models.Message.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))