"""
Scoring helpers: task-based AI exposure, career/market stress, financial ROI stress,
and composite overall “cooked”. AI replacement risk is primarily from Claude; when
`tasks` are provided, we derive a time-weighted score in Python.
"""

from __future__ import annotations

from typing import Any

from backend.models import JobTaskExposure

# Horizons treated as “near term” for a separate meter (0–2y vibe)
_NEAR_TERM_HORIZONS = frozenset({"now", "1_2_years"})

# Light calibration: small upward nudge to account for the pace of AI tooling adoption.
# Kept mild so that genuinely low-risk roles stay low and the score feels honest.
_CALIBRATION_LIFT_RATIO = 0.06
_CALIBRATION_FLOOR_BUMP = 2


def harsh_calibrate_automation_0_100(raw: int) -> int:
    """
    Mild upward calibration — accounts for fast-moving tooling adoption without
    inflating scores so much that every career looks doomed.
    """
    try:
        x = int(raw)
    except (TypeError, ValueError):
        x = 50
    x = max(0, min(100, x))
    lifted = x + (100 - x) * _CALIBRATION_LIFT_RATIO + _CALIBRATION_FLOOR_BUMP
    return max(0, min(100, int(round(lifted))))


def _trend_stress_0_100(job_market_trend: str | None) -> int:
    if job_market_trend == "shrinking":
        return 85
    if job_market_trend == "flat":
        return 55
    if job_market_trend == "growing":
        return 30
    return 50


def compute_financial_roi_stress_0_100(
    estimated_tuition: int | None,
    tuition_if_invested: int | None,
) -> int:
    if not estimated_tuition or estimated_tuition <= 0:
        return 40
    if not tuition_if_invested:
        return 45
    gap = tuition_if_invested - estimated_tuition
    if gap <= 0:
        return 25
    ratio = gap / estimated_tuition
    return min(100, int(35 + ratio * 25))


def compute_career_market_stress_0_100(
    job_market_trend: str | None,
    unemployment_rate_pct: float | None,
) -> int:
    """
    Higher = worse (stagnation / headwinds). Blends trend with optional unemployment nudge.
    """
    base = _trend_stress_0_100(job_market_trend)
    if unemployment_rate_pct is None:
        return base
    u = float(unemployment_rate_pct)
    if u <= 6:
        return base
    bump = min(18, int((u - 6) * 2.2))
    return min(100, base + bump)


def compute_overall_cooked_from_components(
    ai_replacement_risk_0_100: int,
    career_market_stress_0_100: int,
    financial_roi_stress_0_100: int,
) -> int:
    """
    Composite cooked: 45% AI exposure + 30% career/market stress + 25% financial stress.
    Only pulls overall up to AI risk when AI risk is extreme (>85) and the other
    signals also look bad — otherwise the blend speaks for itself.
    """
    raw = (
        0.45 * ai_replacement_risk_0_100
        + 0.30 * career_market_stress_0_100
        + 0.25 * financial_roi_stress_0_100
    )
    out = max(0, min(100, int(round(raw))))
    if ai_replacement_risk_0_100 > 85 and career_market_stress_0_100 > 50:
        out = max(out, ai_replacement_risk_0_100 - 10)
    return out


def compute_overall_cooked_0_100(
    ai_replacement_risk_0_100: int,
    job_market_trend: str | None,
    estimated_tuition: int | None,
    tuition_if_invested: int | None,
    unemployment_rate_pct: float | None = None,
) -> int:
    """Backward-compatible wrapper using the same component blend."""
    c = compute_career_market_stress_0_100(job_market_trend, unemployment_rate_pct)
    f = compute_financial_roi_stress_0_100(estimated_tuition, tuition_if_invested)
    return compute_overall_cooked_from_components(ai_replacement_risk_0_100, c, f)


def financial_opportunity_gap(
    estimated_tuition: int | None,
    tuition_if_invested: int | None,
) -> int | None:
    if estimated_tuition is None or tuition_if_invested is None:
        return None
    return tuition_if_invested - estimated_tuition


def _normalize_time_weights(raw: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
    """Return (normalized_weight_0_1, task_dict) per row; weights sum to 1."""
    weights: list[float] = []
    rows: list[dict[str, Any]] = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        try:
            pct = int(d.get("time_pct") or 0)
        except (TypeError, ValueError):
            pct = 0
        pct = max(0, min(100, pct))
        if pct <= 0:
            continue
        weights.append(float(pct))
        rows.append(d)
    s = sum(weights)
    if s <= 0:
        return []
    return [(w / s, r) for w, r in zip(weights, rows)]


def compute_task_based_ai_metrics(
    raw_tasks: list[dict[str, Any]],
) -> tuple[int | None, int | None, list[JobTaskExposure]]:
    """
    Time-weighted automation exposure from task decomposition.
    Returns (overall_0_100, near_term_0_100 or None, validated task rows).
    """
    if not raw_tasks:
        return None, None, []

    normed = _normalize_time_weights(raw_tasks)
    if not normed:
        return None, None, []

    out_models: list[JobTaskExposure] = []
    overall = 0.0
    near_num = 0.0
    near_den = 0.0

    for w, d in normed:
        try:
            score = int(d.get("automation_score_0_100", 50))
        except (TypeError, ValueError):
            score = 50
        score = harsh_calibrate_automation_0_100(score)
        hz = str(d.get("timeline_horizon") or "longer").strip().lower()
        if hz not in ("now", "1_2_years", "3_5_years", "longer"):
            hz = "longer"
        task_label = str(d.get("task") or "")[:500]
        reason = str(d.get("reasoning") or "")[:1200]
        try:
            tp = int(d.get("time_pct") or 0)
        except (TypeError, ValueError):
            tp = 0
        tp = max(0, min(100, tp))
        out_models.append(
            JobTaskExposure(
                task=task_label,
                time_pct=tp,
                automation_score_0_100=score,
                reasoning=reason,
                timeline_horizon=hz,
            )
        )
        overall += w * score
        if hz in _NEAR_TERM_HORIZONS:
            near_num += w * score
            near_den += w

    o = int(round(max(0, min(100, overall))))
    near: int | None
    if near_den > 0:
        near = int(round(max(0, min(100, near_num / near_den))))
    else:
        near = None
    return o, near, out_models


def resolve_ai_replacement_from_llm(
    ai_from_llm: int,
    ai_risk_reasoning: str,
    raw_tasks: list[dict[str, Any]] | None,
) -> tuple[int, str, list[JobTaskExposure], int | None]:
    """
    If tasks are present and valid, override scalar AI risk with the weighted task score.
    """
    if not raw_tasks:
        harsh_scalar = harsh_calibrate_automation_0_100(ai_from_llm)
        note = f"Pessimism-calibrated AI exposure (no task list): {harsh_scalar}/100."
        merged = f"{note}\n{ai_risk_reasoning}".strip() if ai_risk_reasoning else note
        return harsh_scalar, merged, [], None

    overall, near, models = compute_task_based_ai_metrics(raw_tasks)
    if overall is None:
        harsh_scalar = harsh_calibrate_automation_0_100(ai_from_llm)
        note = f"Pessimism-calibrated AI exposure (tasks invalid; scalar fallback): {harsh_scalar}/100."
        merged = f"{note}\n{ai_risk_reasoning}".strip() if ai_risk_reasoning else note
        return harsh_scalar, merged, [], None

    note = (
        f"Composite AI exposure (time-weighted, pessimism-calibrated from {len(models)} tasks): "
        f"{overall}/100."
    )
    merged = f"{note}\n{ai_risk_reasoning}".strip() if ai_risk_reasoning else note
    return overall, merged, models, near
