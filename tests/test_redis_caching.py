import pytest
from app import cache
from app.middleware.rate_limit import rate_limit_middleware


def test_cache_set_and_get_memory(monkeypatch):
    """Keshga yozish va o'qish funksiyalarini tekshirish"""
    # Soxta xotira lug'ati orqali Redisni tekshirish
    store = {}

    monkeypatch.setattr(cache.redis_client, "get", lambda k: store.get(k))
    monkeypatch.setattr(cache.redis_client, "setex", lambda k, ttl, v: store.update({k: v}))
    monkeypatch.setattr(cache.redis_client, "delete", lambda *keys: [store.pop(k, None) for k in keys])
    monkeypatch.setattr(cache.redis_client, "keys", lambda pattern: list(store.keys()))

    # 1. Keshga yozish
    assert cache.cache_set("test:key", {"message": "salom"}, ttl=60) is True

    # 2. Keshdan o'qish
    data = cache.cache_get("test:key")
    assert data == {"message": "salom"}

    # 3. Keshdan o'chirish
    assert cache.cache_delete("test:key") is True
    assert cache.cache_get("test:key") is None


def test_post_caching_flow(client, authorized_client, test_posts, monkeypatch):
    """Postlarni o'qish va keshdan qaytarish oqimi"""
    store = {}

    monkeypatch.setattr(cache.redis_client, "get", lambda k: store.get(k))
    monkeypatch.setattr(cache.redis_client, "setex", lambda k, ttl, v: store.update({k: v}))
    monkeypatch.setattr(cache.redis_client, "delete", lambda *keys: [store.pop(k, None) for k in keys])
    monkeypatch.setattr(
        cache.redis_client,
        "keys",
        lambda pattern: [k for k in store if k.startswith(pattern.replace("*", ""))]
    )

    # 1. Birinchi so'rov (Cache Miss -> DB dan olib keshga yozadi)
    res1 = client.get("/posts/")
    assert res1.status_code == 200
    assert len(store) > 0

    # 2. Ikkinchi so'rov (Cache Hit -> Keshdan oladi)
    res2 = client.get("/posts/")
    assert res2.status_code == 200
    assert res2.json() == res1.json()

    # 3. Yangi post yaratilganda keshning tozalanishi
    create_res = authorized_client.post(
        "/posts/",
        json={"title": "Yangi post", "body": "Yangi matn", "published": True}
    )
    assert create_res.status_code == 201

    # Ro'yxat keshi o'chirilgan bo'lishi kerak
    list_cache_keys = [k for k in store if k.startswith("posts:all:")]
    assert len(list_cache_keys) == 0
