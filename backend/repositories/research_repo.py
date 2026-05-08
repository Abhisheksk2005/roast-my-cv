from __future__ import annotations

import json
from typing import Any

from backend.models import ReportCard, ResearchData, Session


def research_report_card_from_session(session: Session) -> dict[str, Any] | None:
    """Serialize research + report card for cache/API payloads."""
    if not session.research:
        return None
    return {
        "research": session.research.model_dump(mode="json"),
        "report_card": session.report_card.model_dump(mode="json") if session.report_card else None,
    }


def cache_key_research(session_id: str) -> str:
    return f"donald:research:{session_id}"


def cache_key_task_result(task_id: str) -> str:
    return f"donald:task:{task_id}"


def serialize_task_result(
    *,
    research: ResearchData,
    grade: str,
    score: int,
    report_card: ReportCard | None,
) -> str:
    return json.dumps(
        {
            "research": research.model_dump(mode="json"),
            "grade": grade,
            "score": score,
            "report_card": report_card.model_dump(mode="json") if report_card else None,
        }
    )
