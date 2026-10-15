from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .routers import posts, users, auth
from .config import settings
from .database import get_db

# FastAPI ilovasini yaratish (Production uchun docs ni yashirish sharti bilan)
app = FastAPI(
    title="Professional Blog API",
    description="FastAPI + PostgreSQL + SQLAlchemy + JWT + Alembic + CORS",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

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

@app.get("/")
def root():
    return {
        "xabar": "Blog API ga xush kelibsiz! v5.0",
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