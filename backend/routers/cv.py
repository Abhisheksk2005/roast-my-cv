"""CV upload + coaching analysis endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from backend.services.cv_service import (
    MAX_CV_BYTES,
    extract_cv_text,
    analyze_cv,
)
from backend.session_id import ensure_session_id

router = APIRouter()
logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _validate_extension(filename: str) -> None:
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )


@router.post("/api/cv/upload")
async def upload_cv(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = None,
):
    """Upload a CV (PDF, DOCX, or TXT) and get Claude-powered coaching analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    _validate_extension(file.filename)

    raw = await file.read()
    if len(raw) > MAX_CV_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_CV_BYTES // (1024 * 1024)} MB.",
        )
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    try:
        cv_text = extract_cv_text(raw, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse the file. Is it a valid PDF or DOCX?")

    if not cv_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract any text from the file. Try a different format or check the file.",
        )

    try:
        analysis = await analyze_cv(cv_text, file.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        logger.exception("cv_analysis_unhandled_error", filename=file.filename)
        raise HTTPException(
            status_code=502,
            detail="CV analysis failed unexpectedly. Check backend logs for details.",
        )

    store = request.app.state.store
    if session_id:
        try:
            ensure_session_id(session_id)
            await store.update_cv_analysis(session_id, analysis)
        except Exception:
            pass

    return {
        "analysis": analysis.model_dump(mode="json"),
        "session_id": session_id,
    }


@router.get("/api/cv/analysis/{session_id}")
async def get_cv_analysis(session_id: str, request: Request):
    """Retrieve a previously stored CV analysis for a session."""
    ensure_session_id(session_id)
    store = request.app.state.store
    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.cv_analysis:
        raise HTTPException(status_code=404, detail="No CV analysis found for this session")
    return {"analysis": session.cv_analysis.model_dump(mode="json")}
