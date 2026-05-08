from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import Request

from backend.redis_client import get_async_redis

VOICE_DAILY_MAX_SESSIONS = int((os.getenv("VOICE_DAILY_MAX_SESSIONS") or "3").strip())


def voice_limits_disabled() -> bool:
    return (os.getenv("VOICE_LIMITS_DISABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ) or (os.getenv("RATE_LIMIT_DISABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _utc_day(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _seconds_until_next_utc_day(now: datetime) -> int:
    tomorrow = (now + timedelta(days=1)).date()
    next_midnight = datetime(
        tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc
    )
    return max(1, int((next_midnight - now).total_seconds()))


async def consume_voice_session_for_today(
    request: Request,
) -> tuple[bool, int]:
    """
    Consume one voice session for this client for the current UTC day.
    Returns (allowed, retry_after_seconds).
    """
    if voice_limits_disabled():
        return True, 0

    now = datetime.now(timezone.utc)
    day = _utc_day(now)
    retry_after = _seconds_until_next_utc_day(now)
    client_id = _client_id(request)

    r = await get_async_redis()
    if r:
        key = f"voice:daily:{day}:{client_id}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, retry_after + 60)
        if count > VOICE_DAILY_MAX_SESSIONS:
            await r.decr(key)
            return False, retry_after
        return True, 0

    if not hasattr(request.app.state, "_voice_daily_counts"):
        request.app.state._voice_daily_counts = {}  # type: ignore[attr-defined]
    mem: dict[tuple[str, str], int] = request.app.state._voice_daily_counts  # type: ignore[assignment]

    # Tiny cleanup so memory does not grow forever.
    stale_days = {k for k in mem.keys() if k[0] != day}
    for k in stale_days:
        mem.pop(k, None)

    k = (day, client_id)
    count = int(mem.get(k, 0))
    if count >= VOICE_DAILY_MAX_SESSIONS:
        return False, retry_after
    mem[k] = count + 1
    return True, 0

