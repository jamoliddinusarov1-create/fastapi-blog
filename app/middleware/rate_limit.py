import os
import time
import logging
from fastapi import Request, HTTPException, status
from ..cache import redis_client

logger = logging.getLogger(__name__)


async def rate_limit_middleware(
    request: Request,
    calls: int = 100,  # Max so'rovlar
    period: int = 60   # Sekund
):
    """
    calls: Ruxsat etilgan so'rovlar soni
    period: Vaqt oralig'i (sekund)
    """
    # Avtotestlar (pytest) paytida test mijozlarini bloklamaslik (agar maxsus test bo'lmasa)
    if "PYTEST_CURRENT_TEST" in os.environ and not request.headers.get("X-Test-Rate-Limit"):
        return 0

    # IP manzil olish
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = f"rate_limit:{client_ip}:{request.url.path}"

    try:
        # Hozirgi vaqt (oyna boshlanishi)
        current = int(time.time())
        window_start = current - period

        # Redis pipeline (bir nechta buyruq birga)
        pipe = redis_client.pipeline()
        # Eski so'rovlarni o'chirish
        pipe.zremrangebyscore(key, 0, window_start)
        # Hozirgi so'rovni qo'shish
        pipe.zadd(key, {str(current): current})
        # Oynada nechta so'rov borligini hisoblash
        pipe.zcard(key)
        # TTL o'rnatish (eski ma'lumot tozalansin)
        pipe.expire(key, period)
        results = pipe.execute()

        request_count = results[2]
        if request_count > calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "xato": "Juda ko'p so'rov!",
                    "limit": calls,
                    "period": f"{period} sekund",
                    "qayta_urinish": f"{period} sekunddan keyin"
                },
                headers={"Retry-After": str(period)}
            )
        return request_count
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Rate limit xatosi (Redis): {e}")
        return 0
