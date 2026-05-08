from fastapi import APIRouter, Request

from backend.services.public_metrics_service import (
    get_public_metrics,
    recompute_public_metrics,
)

router = APIRouter()


@router.get("/api/public-metrics")
async def public_metrics_get(request: Request):
    store = request.app.state.store
    metrics = await get_public_metrics(store)
    return {"metrics": metrics}


@router.post("/api/public-metrics/recompute")
async def public_metrics_recompute(request: Request):
    store = request.app.state.store
    metrics = await recompute_public_metrics(store)
    return {"ok": True, "metrics": metrics}


