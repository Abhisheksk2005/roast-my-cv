from fastapi import APIRouter, HTTPException, Request

from backend.session_id import ensure_session_id

router = APIRouter()


@router.get("/api/report-card/{session_id}")
async def get_report_card(session_id: str, request: Request):
    ensure_session_id(session_id)
    store = request.app.state.store
    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.report_card:
        raise HTTPException(status_code=404, detail="Report card not generated yet")
    card = session.report_card.model_dump()
    if "profile" in card and "salary" in card["profile"]:
        del card["profile"]["salary"]
    return {"report_card": card}
