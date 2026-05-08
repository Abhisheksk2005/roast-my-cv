from backend.models import ResearchData


def _career_quality_0_100(research: ResearchData, salary: int | None) -> int:
    """Legacy factors: salary vs degree benchmark, ROI-ish, job trend, tuition vs invested."""
    factors: list[tuple[float, float]] = []

    effective_salary = salary or research.avg_salary_for_degree

    if effective_salary and research.avg_salary_for_degree:
        ratio = effective_salary / research.avg_salary_for_degree
        score = min(max((ratio - 0.5) / 1.0, 0.0), 1.0)
        factors.append((0.3, score))

    if effective_salary and research.estimated_tuition:
        ten_year_earnings = effective_salary * 10
        roi = (ten_year_earnings - research.estimated_tuition) / research.estimated_tuition
        score = min(max((roi - 0) / 10, 0.0), 1.0)
        factors.append((0.3, score))

    if research.job_market_trend:
        trend_scores = {"growing": 0.9, "flat": 0.5, "shrinking": 0.15}
        score = trend_scores.get(research.job_market_trend, 0.5)
        factors.append((0.2, score))

    if research.estimated_tuition and research.tuition_if_invested:
        gap_ratio = research.tuition_if_invested / research.estimated_tuition
        score = min(max(1.0 - (gap_ratio - 1.0) / 4.0, 0.0), 1.0)
        factors.append((0.2, score))

    if not factors:
        return 50

    total_weight = sum(w for w, _ in factors)
    weighted = sum(w * s for w, s in factors) / total_weight
    return int(min(max(weighted * 100, 0), 100))


def compute_grade(
    research: ResearchData,
    salary: int | None = None,
    years_experience: int | None = None,
) -> tuple[str, int]:
    """
    Letter grade + 0–100 score.
    Career quality is the primary signal; AI risk is a meaningful drag but not
    the whole story — a nurse or plumber with low AI risk shouldn't get punished
    just because the system defaults to doom.
    """
    career = _career_quality_0_100(research, salary)
    ai = research.ai_replacement_risk_0_100
    if ai is None:
        ai = 50

    # 60 % career fundamentals, 40 % AI-resilience
    survival = int(0.60 * career + 0.40 * (100 - ai))

    if years_experience is not None and years_experience >= 10:
        survival = min(100, survival + 5)
    elif years_experience is not None and years_experience <= 1:
        survival = max(0, survival - 3)

    # High AI risk still caps upside, but less aggressively than before
    if ai > 75:
        cap = int(75 - (ai - 75) * 0.8)
        cap = max(30, min(70, cap))
        survival = min(survival, cap)

    grade_score = min(max(survival, 0), 100)

    # Only force an F when the picture is unambiguously dire: at least two of the
    # three risk signals must be extreme, not just one outlier.
    ai_now = ai
    ai_near = research.near_term_ai_risk_0_100 or 0
    cooked = research.overall_cooked_0_100 or 0
    extreme_count = sum(1 for v in (ai_now, ai_near, cooked) if v > 80)
    if extreme_count >= 2:
        grade_score = min(grade_score, 34)
        return ("F", grade_score)

    if grade_score >= 80:
        grade = "A"
    elif grade_score >= 65:
        grade = "B"
    elif grade_score >= 50:
        grade = "C"
    elif grade_score >= 35:
        grade = "D"
    else:
        grade = "F"

    return (grade, grade_score)
