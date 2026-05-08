"""Log request activity to Firestore (optional)."""

from __future__ import annotations

import os
import re
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.database import get_async_firestore
from backend.repositories.activity_repo import hash_client_ip, log_activity_event

logger = structlog.get_logger(__name__)

SESSION_PATH = re.compile(r"/api/(?:report-card|session)/([0-9a-fA-F-]{36})")


def _extract_session_id(path: str, method: str) -> str | None:
    m = SESSION_PATH.search(path)
    if m:
        return m.group(1)
    return None


class ActivityTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (os.getenv("ACTIVITY_TRACKING_DISABLED") or "").strip().lower() in ("1", "true", "yes"):
            return await call_next(request)

        start = time.perf_counter()
        db = get_async_firestore()
        path = request.url.path
        method = request.method
        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent") or ""
        rid = getattr(request.state, "request_id", None) or str(uuid.uuid4())

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        session_id = _extract_session_id(path, method)

        if db:
            try:
                await log_activity_event(
                    db,
                    client_ip_hashed=hash_client_ip(ip),
                    session_id=session_id,
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    user_agent=ua,
                    request_id=rid,
                    metadata={},
                )
            except Exception as exc:
                logger.warning("activity_log_failed", error=str(exc))

        return response
