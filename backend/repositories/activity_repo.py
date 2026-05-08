from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud.firestore_v1.async_client import AsyncClient

COLLECTION = "activity_events"


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]


async def log_activity_event(
    db: AsyncClient,
    *,
    client_ip_hashed: str,
    session_id: str | None,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_agent: str,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    event_id = str(uuid.uuid4())
    doc = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_ip_hashed": client_ip_hashed,
        "session_id": session_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "user_agent": (user_agent or "")[:512],
        "metadata": metadata or {},
        "request_id": request_id,
    }
    await db.collection(COLLECTION).document(event_id).set(doc)


def hash_client_ip(ip: str | None) -> str:
    if not ip:
        return ""
    return _hash_ip(ip.strip())
