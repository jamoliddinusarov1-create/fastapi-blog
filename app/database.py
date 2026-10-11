from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# PostgreSQL ulanish engine'i
engine = create_engine(settings.database_url)

# Har bir so'rov uchun session yaratuvchi
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# SQLAlchemy modellar uchun asosiy Base klassi
Base = declarative_base()

# Dependency (har bir endpoint uchun DB session berish va yopish)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()