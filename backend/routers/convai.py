import os

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

ELEVEN_TOKEN_URL = "https://api.elevenlabs.io/v1/convai/conversation/token"


def _allowed_agent_ids() -> set[str]:
    # Allow either a comma-separated allowlist or a single fixed id.
    raw = (os.getenv("ELEVENLABS_ALLOWED_AGENT_IDS") or "").strip()
    if raw:
        return {x.strip() for x in raw.split(",") if x.strip()}
    single = (os.getenv("ELEVENLABS_AGENT_ID") or "").strip()
    return {single} if single else set()


@router.get("/api/convai/conversation-token")
async def conversation_token(
    agent_id: str = Query(..., description="Same id as NEXT_PUBLIC_ELEVENLABS_AGENT_ID"),
    branch_id: str | None = Query(
        None,
        description="Optional ElevenLabs branch (draft) id, e.g. from URL branchId=",
    ),
):
    """
    Mint a short-lived WebRTC token using your workspace API key.
    The key never goes to the browser — only this server calls ElevenLabs.
    Use when the agent has authentication / private access enabled.
    """
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ELEVENLABS_API_KEY is not set on the server. Add it to backend/.env or use a public agent with NEXT_PUBLIC_ELEVENLABS_USE_TOKEN=false.",
        )

    allowed = _allowed_agent_ids()
    if allowed and agent_id not in allowed:
        raise HTTPException(
            status_code=403,
            detail="agent_id is not allowed for token minting on this server",
        )

    params: dict[str, str] = {"agent_id": agent_id}
    if branch_id:
        params["branch_id"] = branch_id

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            ELEVEN_TOKEN_URL,
            params=params,
            headers={"xi-api-key": api_key},
            timeout=30.0,
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=resp.text[:2000] or "ElevenLabs token request failed",
        )

    data = resp.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=502, detail="ElevenLabs response missing token")

    return {"token": token}
