import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.models import UserProfile
from backend.session_id import ensure_session_id
from backend.services.voice_limits import (
    VOICE_DAILY_MAX_SESSIONS,
    consume_voice_session_for_today,
    voice_limits_disabled,
)

router = APIRouter()
VOICE_SESSION_MAX_SECONDS = int((os.getenv("VOICE_SESSION_MAX_SECONDS") or "180").strip())


class SessionRequest(BaseModel):
    name: str
    degree: str
    university: str
    graduation_year: int
    current_job: str
    current_company: str = ""
    salary: int | None = None
    years_experience: int | None = None
    source: str = "manual"


class SessionResponse(BaseModel):
    session_id: str


@router.post("/api/session", response_model=SessionResponse)
async def create_session(req: SessionRequest, request: Request):
    source = (req.source or "").strip().lower()
    if source == "voice":
        allowed, retry_after = await consume_voice_session_for_today(request)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily voice limit reached ({VOICE_DAILY_MAX_SESSIONS} sessions/day). "
                    "Please come back tomorrow."
                ),
                headers={"Retry-After": str(retry_after)},
            )
    profile = UserProfile(**req.model_dump())
    session_id = await request.app.state.store.create(profile)
    return SessionResponse(session_id=session_id)


@router.get("/api/session/{session_id}/voice-activity")
async def get_voice_activity(session_id: str, request: Request):
    """Poll during voice: server-side webhook + pipeline steps."""
    ensure_session_id(session_id)
    session = await request.app.state.store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not voice_limits_disabled():
        created_at = session.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_sec = (datetime.now(timezone.utc) - created_at).total_seconds()
        if age_sec > VOICE_SESSION_MAX_SECONDS:
            raise HTTPException(
                status_code=429,
                detail="This call has reached the 3-minute daily limit. Please come back tomorrow.",
            )
    return {
        "items": [i.model_dump(mode="json") for i in session.voice_activity],
    }
