from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as aioredis
    import redis as sync_redis


def redis_url() -> str:
    """Broker URL when Redis is enabled; must be non-empty in that case."""
    u = (os.getenv("REDIS_URL") or "").strip()
    return u or "redis://localhost:6379/0"


def redis_enabled() -> bool:
    """Use Redis only when REDIS_URL is set and not explicitly disabled.

    Without REDIS_URL (typical Railway API-only deploy), rate limiting falls back to in-memory.
    """
    if (os.getenv("REDIS_DISABLED") or "").strip().lower() in ("1", "true", "yes"):
        return False
    return bool((os.getenv("REDIS_URL") or "").strip())


@lru_cache(maxsize=1)
def get_sync_redis():
    import redis as sync_redis

    if not redis_enabled():
        raise RuntimeError("Redis disabled (REDIS_DISABLED=1)")
    return sync_redis.from_url(redis_url(), decode_responses=True)


_async_redis = None


async def get_async_redis():
    global _async_redis
    if not redis_enabled():
        return None
    if _async_redis is None:
        import redis.asyncio as aioredis

        _async_redis = aioredis.from_url(redis_url(), decode_responses=True)
    return _async_redis


def clear_redis_cache() -> None:
    global _async_redis
    _async_redis = None
    get_sync_redis.cache_clear()
