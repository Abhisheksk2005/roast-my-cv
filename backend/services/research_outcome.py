"""Shared research → report card pipeline (HTTP, webhooks, Celery)."""

from __future__ import annotations

from backend.models import ReportCard, ResearchData, UserProfile
from backend.services.ai_job_model import (
    compute_career_market_stress_0_100,
    compute_financial_roi_stress_0_100,
    compute_overall_cooked_from_components,
)
from backend.services.grading import compute_grade


def tuition_invested_for_api(r: ResearchData) -> int | None:
    if r.tuition_if_invested is not None:
        return r.tuition_if_invested
    return r.tuition_as_sp500_today


def apply_cooked_components(research: ResearchData) -> ResearchData:
    """Match webhooks.research_degree post-processing."""
    if research.tuition_if_invested is None and research.tuition_as_sp500_today is not None:
        research = research.model_copy(update={"tuition_if_invested": research.tuition_as_sp500_today})
    t_inv = tuition_invested_for_api(research)
    c = compute_career_market_stress_0_100(research.job_market_trend, research.unemployment_rate_pct)
    f = compute_financial_roi_stress_0_100(research.estimated_tuition, t_inv)
    cooked_updates: dict = {"career_market_stress_0_100": c, "financial_roi_stress_0_100": f}
    if research.ai_replacement_risk_0_100 is not None:
        cooked_updates["overall_cooked_0_100"] = compute_overall_cooked_from_components(
            research.ai_replacement_risk_0_100,
            c,
            f,
        )
    return research.model_copy(update=cooked_updates)


def grade_and_report_card(session_id: str, p: UserProfile, research: ResearchData) -> tuple[str, int, ReportCard]:
    p2 = p.model_copy(update={"currency_code": research.currency_code})
    grade, score = compute_grade(research, p2.salary, p2.years_experience)
    report_card = ReportCard(
        session_id=session_id,
        grade=grade,
        grade_score=score,
        profile=p2,
        research=research,
    )
    return grade, score, report_card


def research_result_to_dict(
    research: ResearchData,
    grade: str,
    score: int,
    report_card: ReportCard,
) -> dict:
    return {
        "research": research.model_dump(mode="json"),
        "grade": grade,
        "score": score,
        "report_card": report_card.model_dump(mode="json"),
    }
