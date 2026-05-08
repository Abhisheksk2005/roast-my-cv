"""Redis sliding-window rate limiting per client IP."""

from __future__ import annotations

import os
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.redis_client import get_async_redis

GLOBAL_LIMIT = int((os.getenv("RATE_LIMIT_GLOBAL_PER_MIN") or "100").strip())
GLOBAL_WINDOW = 60
WEBHOOK_DEFAULT_LIMIT = int((os.getenv("RATE_LIMIT_WEBHOOK_PER_MIN") or "20").strip())
WEBHOOK_RESEARCH_LIMIT = int((os.getenv("RATE_LIMIT_WEBHOOK_RESEARCH_PER_MIN") or "6").strip())


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limit_exempt(method: str, path: str) -> bool:
    """
    Public read-only endpoints that should not consume the global per-IP budget.
    Homepage stats (and health) must stay available even when other API routes are hot.
    """
    if method == "GET" and path == "/api/public-metrics":
        return True
    if method == "GET" and path in ("/health", "/ready"):
        return True
    return False


def _endpoint_limit(method: str, path: str) -> tuple[int, int] | None:
    if method == "POST" and path == "/api/session":
        return 10, 60
    if method == "POST" and path == "/api/research":
        return 5, 60
    if method == "POST" and path == "/api/webhooks/research_degree":
        return WEBHOOK_RESEARCH_LIMIT, 60
    if method == "POST" and path.startswith("/api/webhooks/"):
        return WEBHOOK_DEFAULT_LIMIT, 60
    if method == "GET" and path == "/api/convai/conversation-token":
        return 5, 60
    return None


async def _allow_window(r, key: str, limit: int, window_sec: int) -> bool:
    now = time.time()
    await r.zremrangebyscore(key, 0, now - window_sec)
    n = await r.zcard(key)
    if n >= limit:
        return False
    await r.zadd(key, {str(uuid.uuid4()): now})
    await r.expire(key, window_sec + 5)
    return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (os.getenv("RATE_LIMIT_DISABLED") or "").strip().lower() in ("1", "true", "yes"):
            return await call_next(request)

        path = request.url.path
        method = request.method
        if _rate_limit_exempt(method, path):
            return await call_next(request)

        ip = _client_ip(request)
        r = await get_async_redis()

        if r:
            gkey = f"rl:global:{ip}"
            if not await _allow_window(r, gkey, GLOBAL_LIMIT, GLOBAL_WINDOW):
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={"Retry-After": str(GLOBAL_WINDOW)},
                )
            rule = _endpoint_limit(method, path)
            if rule:
                lim, w = rule
                pkey = f"rl:{method}:{path}:{ip}"
                if not await _allow_window(r, pkey, lim, w):
                    return JSONResponse(
                        {"detail": "Rate limit exceeded for this endpoint"},
                        status_code=429,
                        headers={"Retry-After": str(w)},
                    )
        else:
            if not hasattr(request.app.state, "_rate_mem"):
                request.app.state._rate_mem = {}  # type: ignore[attr-defined]
            mem: dict = request.app.state._rate_mem  # type: ignore[assignment]
            now = time.time()
            gkey = ("global", ip)
            arr = [t for t in mem.get(gkey, []) if now - t < GLOBAL_WINDOW]
            arr.append(now)
            mem[gkey] = arr
            if len(arr) > GLOBAL_LIMIT:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
            rule = _endpoint_limit(method, path)
            if rule:
                lim, w = rule
                ekey = (path, method, ip)
                arr2 = [t for t in mem.get(ekey, []) if now - t < w]
                arr2.append(now)
                mem[ekey] = arr2
                if len(arr2) > lim:
                    return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

        return await call_next(request)
