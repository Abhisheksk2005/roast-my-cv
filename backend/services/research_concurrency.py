from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from fastapi import Request

from backend.redis_client import get_async_redis, get_sync_redis, redis_enabled

RESEARCH_MAX_INFLIGHT_PER_IP = int(
    (os.getenv("RESEARCH_MAX_INFLIGHT_PER_IP") or "2").strip()
)
RESEARCH_MAX_INFLIGHT_PER_SESSION = int(
    (os.getenv("RESEARCH_MAX_INFLIGHT_PER_SESSION") or "1").strip()
)
RESEARCH_INFLIGHT_TTL_SEC = int((os.getenv("RESEARCH_INFLIGHT_TTL_SEC") or "900").strip())


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes")


def research_concurrency_disabled() -> bool:
    return _truthy("RESEARCH_CONCURRENCY_DISABLED") or _truthy("RATE_LIMIT_DISABLED")


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _ip_key(ip: str) -> str:
    return f"research:inflight:ip:{ip}"


def _session_key(session_id: str) -> str:
    return f"research:inflight:session:{session_id}"


def _retry_after_from_ttl(ttl_sec: int | None) -> int:
    if ttl_sec is None:
        return max(1, RESEARCH_INFLIGHT_TTL_SEC // 4)
    if ttl_sec < 1:
        return max(1, RESEARCH_INFLIGHT_TTL_SEC // 4)
    return ttl_sec


async def _redis_acquire(
    ip: str, session_id: str
) -> tuple[bool, int, str | None, dict[str, str] | None]:
    r = await get_async_redis()
    if not r:
        return False, 0, "redis_unavailable", None

    ip_key = _ip_key(ip)
    session_key = _session_key(session_id)

    ip_count = int(await r.incr(ip_key))
    if ip_count == 1:
        await r.expire(ip_key, RESEARCH_INFLIGHT_TTL_SEC)
    if ip_count > RESEARCH_MAX_INFLIGHT_PER_IP:
        await r.decr(ip_key)
        ttl = await r.ttl(ip_key)
        return (
            False,
            _retry_after_from_ttl(int(ttl) if isinstance(ttl, int) else None),
            f"Too many in-flight research jobs for this IP (max {RESEARCH_MAX_INFLIGHT_PER_IP}).",
            None,
        )

    session_count = int(await r.incr(session_key))
    if session_count == 1:
        await r.expire(session_key, RESEARCH_INFLIGHT_TTL_SEC)
    if session_count > RESEARCH_MAX_INFLIGHT_PER_SESSION:
        await r.decr(session_key)
        await r.decr(ip_key)
        ttl = await r.ttl(session_key)
        return (
            False,
            _retry_after_from_ttl(int(ttl) if isinstance(ttl, int) else None),
            (
                f"Too many in-flight research jobs for this session "
                f"(max {RESEARCH_MAX_INFLIGHT_PER_SESSION})."
            ),
            None,
        )

    return (
        True,
        0,
        None,
        {"backend": "redis", "ip_key": ip_key, "session_key": session_key},
    )


async def _memory_acquire(
    request: Request, ip: str, session_id: str
) -> tuple[bool, int, str | None, dict[str, str] | None]:
    if not hasattr(request.app.state, "_research_inflight_lock"):
        request.app.state._research_inflight_lock = asyncio.Lock()  # type: ignore[attr-defined]
    if not hasattr(request.app.state, "_research_inflight_mem"):
        request.app.state._research_inflight_mem = {}  # type: ignore[attr-defined]

    lock: asyncio.Lock = request.app.state._research_inflight_lock  # type: ignore[assignment]
    mem: dict[str, dict[str, Any]] = request.app.state._research_inflight_mem  # type: ignore[assignment]

    now = time.time()
    async with lock:
        stale = [
            k
            for k, v in mem.items()
            if (now - float(v.get("updated_at", now))) > RESEARCH_INFLIGHT_TTL_SEC
        ]
        for k in stale:
            mem.pop(k, None)

        ip_key = _ip_key(ip)
        session_key = _session_key(session_id)
        ip_entry = mem.get(ip_key, {"count": 0, "updated_at": now})
        session_entry = mem.get(session_key, {"count": 0, "updated_at": now})
        ip_count = int(ip_entry.get("count", 0))
        session_count = int(session_entry.get("count", 0))

        if ip_count >= RESEARCH_MAX_INFLIGHT_PER_IP:
            return (
                False,
                max(1, RESEARCH_INFLIGHT_TTL_SEC // 4),
                f"Too many in-flight research jobs for this IP (max {RESEARCH_MAX_INFLIGHT_PER_IP}).",
                None,
            )
        if session_count >= RESEARCH_MAX_INFLIGHT_PER_SESSION:
            return (
                False,
                max(1, RESEARCH_INFLIGHT_TTL_SEC // 4),
                (
                    f"Too many in-flight research jobs for this session "
                    f"(max {RESEARCH_MAX_INFLIGHT_PER_SESSION})."
                ),
                None,
            )

        mem[ip_key] = {"count": ip_count + 1, "updated_at": now}
        mem[session_key] = {"count": session_count + 1, "updated_at": now}
        return (
            True,
            0,
            None,
            {"backend": "memory", "ip_key": ip_key, "session_key": session_key},
        )


async def acquire_research_lease(
    request: Request, session_id: str, allow_memory_fallback: bool = True
) -> tuple[bool, int, str | None, dict[str, str] | None]:
    if research_concurrency_disabled():
        return True, 0, None, None

    ip = _client_id(request)
    if redis_enabled():
        ok, retry_after, detail, lease = await _redis_acquire(ip, session_id)
        if ok:
            return ok, retry_after, detail, lease
        if detail != "redis_unavailable":
            return ok, retry_after, detail, lease
    if not allow_memory_fallback:
        return True, 0, None, None
    return await _memory_acquire(request, ip, session_id)


def release_lease_sync(lease: dict[str, str] | None) -> None:
    if not lease:
        return
    if lease.get("backend") != "redis":
        return
    try:
        r = get_sync_redis()
    except Exception:
        return
    ip_key = lease.get("ip_key")
    session_key = lease.get("session_key")
    for key in (ip_key, session_key):
        if not key:
            continue
        try:
            n = int(r.decr(key))
            if n <= 0:
                r.delete(key)
        except Exception:
            continue


async def release_lease_async(request: Request, lease: dict[str, str] | None) -> None:
    if not lease:
        return
    backend = lease.get("backend")
    ip_key = lease.get("ip_key")
    session_key = lease.get("session_key")
    if backend == "redis":
        r = await get_async_redis()
        if not r:
            return
        for key in (ip_key, session_key):
            if not key:
                continue
            try:
                n = int(await r.decr(key))
                if n <= 0:
                    await r.delete(key)
            except Exception:
                continue
        return

    if backend == "memory":
        lock = getattr(request.app.state, "_research_inflight_lock", None)
        mem = getattr(request.app.state, "_research_inflight_mem", None)
        if not lock or not mem:
            return
        async with lock:
            for key in (ip_key, session_key):
                if not key:
                    continue
                entry = mem.get(key)
                if not entry:
                    continue
                count = int(entry.get("count", 0)) - 1
                if count <= 0:
                    mem.pop(key, None)
                else:
                    entry["count"] = count
                    entry["updated_at"] = time.time()
