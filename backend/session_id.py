"""Validate opaque session ids (UUID or demo-* from frontend demo mode)."""

from __future__ import annotations

import re
import uuid

from fastapi import HTTPException

_DEMO = re.compile(r"^demo-[a-z0-9]+$", re.I)


def ensure_session_id(session_id: str) -> str:
    if len(session_id) > 200:
        raise HTTPException(status_code=400, detail="Invalid session id")
    if _DEMO.match(session_id):
        return session_id
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id")
    return session_id
