import os

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.celery_app import celery_app
from backend.services.firecrawl_service import run_research
from backend.services.grading import compute_grade
from backend.services.research_concurrency import (
    acquire_research_lease,
    release_lease_async,
)
from backend.services.research_outcome import apply_cooked_components, grade_and_report_card
from backend.routers.webhooks import ResearchProfilePayload
from backend.session_id import ensure_session_id

router = APIRouter()


class ResearchRequest(BaseModel):
    session_id: str
    profile: ResearchProfilePayload | None = None


def _celery_disabled() -> bool:
    return (os.getenv("CELERY_DISABLED") or "").strip().lower() in ("1", "true", "yes")


@router.post("/api/research")
async def do_research(req: ResearchRequest, request: Request):
    ensure_session_id(req.session_id)
    store = request.app.state.store
    session = await store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    p = req.profile.to_user_profile() if req.profile is not None else session.profile
    profile_dict = p.model_dump(mode="json")
    celery_disabled = _celery_disabled()
    allowed, retry_after, detail, lease = await acquire_research_lease(
        request,
        req.session_id,
        allow_memory_fallback=celery_disabled,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=detail or "Too many in-flight research jobs. Please wait.",
            headers={"Retry-After": str(retry_after)},
        )

    if not celery_disabled:
        from backend.tasks.research_task import run_session_research

        try:
            async_result = run_session_research.delay(req.session_id, profile_dict, lease)
            return JSONResponse(
                status_code=202,
                content={
                    "task_id": async_result.id,
                    "status": "pending",
                    "status_url": f"/api/research/task/{async_result.id}/status",
                    "result_url": f"/api/research/task/{async_result.id}/result",
                },
            )
        except Exception:
            await release_lease_async(request, lease)
            raise

    try:
        research = await run_research(
            degree=p.degree,
            university=p.university,
            graduation_year=p.graduation_year,
            current_job=p.current_job,
            years_experience=p.years_experience,
            salary=p.salary,
            country_or_region=p.country_or_region,
            currency_code=p.currency_code,
            tuition_paid=p.tuition_paid,
            tuition_is_total=p.tuition_is_total,
        )
        research = apply_cooked_components(research)
        await store.update_research(req.session_id, research)
        grade, score, report_card = grade_and_report_card(req.session_id, p, research)
        await store.update_report_card(req.session_id, report_card)

        return {"research": research.model_dump(), "grade": grade, "score": score}
    finally:
        await release_lease_async(request, lease)


@router.get("/api/research/task/{task_id}/status")
async def research_task_status(task_id: str):
    if _celery_disabled():
        raise HTTPException(status_code=503, detail="Celery disabled")
    res = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": res.status,
        "ready": res.ready(),
        "failed": res.failed(),
        "error": str(res.result) if res.failed() else None,
    }


@router.get("/api/research/task/{task_id}/result")
async def research_task_result(task_id: str, request: Request):
    if _celery_disabled():
        raise HTTPException(status_code=503, detail="Celery disabled")
    res = AsyncResult(task_id, app=celery_app)
    if not res.ready():
        raise HTTPException(status_code=404, detail="Task not ready yet")
    if res.failed():
        raise HTTPException(status_code=500, detail=str(res.result))
    from backend.tasks.research_task import parse_task_result

    payload = res.result
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Invalid task result")
    research, grade, score, report_card = parse_task_result(payload)
    store = request.app.state.store
    sid = report_card.session_id
    await store.update_research(sid, research)
    await store.update_report_card(sid, report_card)
    return {"research": research.model_dump(), "grade": grade, "score": score}
