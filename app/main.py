import os
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from .routers import posts, users, auth, websocket, upload
from .config import settings
from .database import get_db

# Logging sozlamalari (6-qism)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# Uploads papkasini yaratish (8-qism)
os.makedirs("uploads", exist_ok=True)

# FastAPI ilovasini yaratish
app = FastAPI(
    title="Professional Blog API",
    description="FastAPI + PostgreSQL + SQLAlchemy + JWT + Alembic + CORS + WebSockets + Background Tasks",
    version="6.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Statik fayllarni ulash (8-qism)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware sozlamasi
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlarni ulash
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(websocket.router)
app.include_router(upload.router)


@app.get("/")
def root():
    return {
        "xabar": "Blog API v7.0 — WebSocket va Background Tasks bilan!",
        "environment": settings.environment
    }


# Health check — server va bazaning ishlashini tekshirish uchun
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "database": db_status,
        "environment": settings.environment
    }