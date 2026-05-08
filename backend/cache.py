from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.redis_client import get_async_redis

T = TypeVar("T", bound=BaseModel)


async def cache_get_json(key: str) -> dict[str, Any] | None:
    r = await get_async_redis()
    if not r:
        return None
    raw = await r.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def cache_set_json(key: str, value: dict[str, Any], ttl_sec: int = 3600) -> None:
    r = await get_async_redis()
    if not r:
        return
    await r.set(key, json.dumps(value), ex=ttl_sec)


async def cache_delete(key: str) -> None:
    r = await get_async_redis()
    if not r:
        return
    await r.delete(key)
