"""Long-running research pipeline for Celery workers."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True, name="research.run_session", max_retries=1, default_retry_delay=30)
def run_session_research(
    self, session_id: str, profile_dict: dict, lease: dict | None = None
) -> dict:
    from backend.database import get_sync_firestore
    from backend.models import ResearchData, UserProfile
    from backend.repositories.session_repo import SyncSessionRepository
    from backend.services.firecrawl_service import run_research
    from backend.services.research_concurrency import release_lease_sync
    from backend.services.research_outcome import (
        apply_cooked_components,
        grade_and_report_card,
        research_result_to_dict,
    )

    p = UserProfile.model_validate(profile_dict)

    async def _run():
        return await run_research(
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

    try:
        try:
            research = asyncio.run(_run())
        except Exception as exc:
            logger.exception("run_research failed for session %s", session_id[:8])
            raise self.retry(exc=exc) from exc

        research = apply_cooked_components(research)
        grade, score, report_card = grade_and_report_card(session_id, p, research)

        db = get_sync_firestore()
        if db:
            repo = SyncSessionRepository(db)
            repo.update_research(session_id, research)
            repo.update_report_card(session_id, report_card)

        return research_result_to_dict(research, grade, score, report_card)
    finally:
        release_lease_sync(lease)


def parse_task_result(payload: dict):
    from backend.models import ReportCard, ResearchData

    research = ResearchData.model_validate(payload["research"])
    grade = str(payload["grade"])
    score = int(payload["score"])
    report_card = ReportCard.model_validate(payload["report_card"])
    return research, grade, score, report_card
