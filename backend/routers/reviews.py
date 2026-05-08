from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.models import PublicReview
from backend.session_id import ensure_session_id

router = APIRouter()


class SubmitReviewRequest(BaseModel):
    session_id: str
    quote: str = Field(min_length=8, max_length=280)
    reviewer_name: str | None = Field(default=None, max_length=80)


@router.post("/api/reviews")
async def submit_review(req: SubmitReviewRequest, request: Request):
    ensure_session_id(req.session_id)
    store = request.app.state.store
    session = await store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.report_card:
        raise HTTPException(status_code=400, detail="Report card not generated yet")

    card = session.report_card
    profile = card.profile
    quote = req.quote.strip()
    reviewer_name = (req.reviewer_name or profile.name or "Anonymous").strip()

    review = PublicReview(
        session_id=req.session_id,
        quote=quote,
        reviewer_name=reviewer_name,
        degree=profile.degree,
        university=profile.university,
        grade=card.grade,
        grade_score=card.grade_score,
        overall_cooked_0_100=card.research.overall_cooked_0_100,
        ai_replacement_risk_0_100=card.research.ai_replacement_risk_0_100,
    )
    saved = await store.create_review(review)
    return {"review": saved.model_dump(mode="json")}


@router.get("/api/reviews")
async def list_reviews(
    request: Request,
    limit: int = Query(default=20, ge=1, le=24),
):
    store = request.app.state.store
    reviews = await store.list_reviews(limit=limit)
    return {"reviews": [r.model_dump(mode="json") for r in reviews]}
