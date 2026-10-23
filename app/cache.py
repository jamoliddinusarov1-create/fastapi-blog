import json
import logging
from typing import Any, Optional
import redis

from .config import settings

logger = logging.getLogger(__name__)

# Redis ulanish
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True  # Bytes → String avtomatik
)


def cache_get(key: str) -> Optional[Any]:
    """Redis dan qiymat olish"""
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning(f"Cache get xato: {e}")
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Redis ga qiymat saqlash"""
    try:
        if ttl is None:
            ttl = settings.cache_ttl
        redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)  # datetime va boshqa obyektlar uchun str
        )
        return True
    except Exception as e:
        logger.warning(f"Cache set xato: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Redis dan bitta kalitni o'chirish"""
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete xato: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Pattern bo'yicha kalitlarni o'chirish (masalan: 'posts:*')"""
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            return len(keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache pattern delete xato: {e}")
        return 0


def cache_exists(key: str) -> bool:
    """Kalit mavjudligini tekshirish"""
    try:
        return bool(redis_client.exists(key))
    except Exception:
        return False
