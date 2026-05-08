from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.database import get_async_firestore, get_sync_firestore
from backend.models import ReportCard, ResearchData, Session, UserProfile

METRICS_COLLECTION = "public_metrics"
METRICS_DOC_ID = "homepage"
SESSIONS_COLLECTION = "sessions"
CONTRIB_COLLECTION = "public_metrics_contrib"


def _session_to_firestore_doc(session: Session) -> dict[str, Any]:
    return {
        "profile": session.profile.model_dump(mode="json"),
        "research": session.research.model_dump(mode="json") if session.research else None,
        "report_card": session.report_card.model_dump(mode="json") if session.report_card else None,
        "created_at": session.created_at,
        "voice_activity": [i.model_dump(mode="json") for i in session.voice_activity],
    }


def _format_compact_usd(n: int) -> str:
    sign = "-" if n < 0 else ""
    x = abs(n)
    if x >= 1_000_000_000:
        return f"{sign}${x / 1_000_000_000:.1f}B"
    if x >= 1_000_000:
        return f"{sign}${x / 1_000_000:.1f}M"
    if x >= 1_000:
        return f"{sign}${x / 1_000:.1f}K"
    return f"{sign}${x:,}"


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        n = int(v)
    except (ValueError, TypeError):
        return None
    return n


def _tuition_gap_positive_usd(card: ReportCard) -> int:
    """Opportunity-cost gap for one card (same as contrib + aggregate). Not FX-normalized; field name is legacy USD."""
    r = card.research
    gap = _safe_int(r.tuition_opportunity_gap)
    if gap is None and r.estimated_tuition is not None and r.tuition_if_invested is not None:
        gap = int(r.tuition_if_invested - r.estimated_tuition)
    if gap is not None and gap > 0:
        return int(gap)
    return 0


def _normalize_regret_sum_0_5(
    *,
    total_cards: int,
    regret_sum_0_5: float,
    regret_score_hint: Any = None,
) -> float:
    """
    Normalize regret sum to a true 0..5-per-card scale.
    Handles legacy snapshots where regret was accidentally stored as 0..100.
    """
    total = max(0, int(total_cards))
    if total == 0:
        return 0.0
    try:
        s = max(0.0, float(regret_sum_0_5))
    except Exception:
        s = 0.0

    avg = s / total
    # Legacy bug shape: average looked like 30.1/5 (actually 0..100 scale).
    if avg > 5.0 and avg <= 100.0:
        s = s / 20.0
        avg = s / total

    # Optional hint fallback from regret_score field.
    if avg > 5.0 and regret_score_hint is not None:
        try:
            hint = float(regret_score_hint)
            if 0.0 <= hint <= 5.0:
                s = hint * total
            elif 5.0 < hint <= 100.0:
                s = (hint / 20.0) * total
        except Exception:
            pass

    # Hard safety clamp.
    return min(max(0.0, s), 5.0 * total)


def _snapshot_to_canonical(snapshot: dict[str, Any]) -> dict[str, Any]:
    total = int(snapshot.get("total_cards") or snapshot.get("degrees_cooked") or 0)
    people = int(snapshot.get("people_talked_to_donald") or total)
    c_count = int(snapshot.get("c_or_worse_count") or 0)
    if c_count == 0 and total > 0 and "c_or_worse_pct" in snapshot:
        try:
            c_count = int(round((float(snapshot.get("c_or_worse_pct") or 0.0) / 100.0) * total))
        except Exception:
            c_count = 0

    tuition = int(snapshot.get("tuition_in_shambles_usd") or 0)
    regret_sum = float(snapshot.get("regret_sum_0_5") or 0.0)
    if regret_sum == 0.0 and total > 0 and "regret_score_0_5" in snapshot:
        try:
            regret_sum = float(snapshot.get("regret_score_0_5") or 0.0) * total
        except Exception:
            regret_sum = 0.0
    regret_sum = _normalize_regret_sum_0_5(
        total_cards=total,
        regret_sum_0_5=regret_sum,
        regret_score_hint=snapshot.get("regret_score_0_5"),
    )

    updated_at = snapshot.get("updated_at")
    if not isinstance(updated_at, str) or not updated_at.strip():
        updated_at = datetime.now(timezone.utc).isoformat()

    return _render_aggregate_snapshot(
        total_cards=max(0, total),
        people_talked_to_donald=max(0, people),
        c_or_worse_count=max(0, c_count),
        tuition_in_shambles_usd=max(0, tuition),
        regret_sum_0_5=regret_sum,
        updated_at=updated_at,
    )


def _compute_from_cards(cards: list[ReportCard], *, people_count: int | None = None) -> dict[str, Any]:
    total = len(cards)
    people = max(0, int(people_count if people_count is not None else total))
    if total == 0:
        return {
            "total_cards": 0,
            "c_or_worse_count": 0,
            "regret_sum_0_5": 0.0,
            "degrees_cooked": 0,
            "people_talked_to_donald": people,
            "c_or_worse_pct": 0.0,
            "tuition_in_shambles_usd": 0,
            "regret_score_0_5": 0.0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "display": {
                "degrees_cooked": "0+",
                "people_talked_to_donald": f"{people:,}+",
                "c_or_worse_pct": "0%",
                "tuition_in_shambles": "$0",
                "regret_score": "0.0/5",
            },
        }

    c_or_worse = 0
    tuition_in_shambles = 0
    regret_samples: list[float] = []
    for card in cards:
        grade = (card.grade or "").strip().upper()
        if grade in {"C", "D", "F"}:
            c_or_worse += 1

        tuition_in_shambles += _tuition_gap_positive_usd(card)

        r = card.research
        cooked = _safe_int(r.overall_cooked_0_100)
        if cooked is None:
            cooked = _safe_int(r.ai_replacement_risk_0_100) or 50
        regret_samples.append(max(0.0, min(5.0, cooked / 20.0)))

    pct = round((c_or_worse / total) * 100, 1)
    regret = round(sum(regret_samples) / len(regret_samples), 1) if regret_samples else 0.0

    regret_sum = round(sum(regret_samples), 4) if regret_samples else 0.0

    return {
        "total_cards": total,
        "c_or_worse_count": c_or_worse,
        "regret_sum_0_5": regret_sum,
        "degrees_cooked": total,
        "people_talked_to_donald": people,
        "c_or_worse_pct": pct,
        "tuition_in_shambles_usd": tuition_in_shambles,
        "regret_score_0_5": regret,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "display": {
            "degrees_cooked": f"{total:,}+",
            "people_talked_to_donald": f"{people:,}+",
            "c_or_worse_pct": f"{round(pct)}%",
            "tuition_in_shambles": _format_compact_usd(tuition_in_shambles),
            "regret_score": f"{regret:.1f}/5",
        },
    }


async def _collect_report_cards(store) -> list[ReportCard]:
    cards: list[ReportCard] = []

    if getattr(store, "uses_firestore", False):
        db = get_async_firestore()
        if not db:
            return cards
        async for doc in db.collection(SESSIONS_COLLECTION).stream():
            data = doc.to_dict() or {}
            raw_card = data.get("report_card")
            if not isinstance(raw_card, dict):
                continue
            try:
                cards.append(ReportCard.model_validate(raw_card))
            except Exception:
                continue
        return cards

    memory = getattr(store, "_memory", {})
    for session in memory.values():
        if isinstance(session, Session) and session.report_card:
            cards.append(session.report_card)
    return cards


async def _count_sessions(store) -> int:
    if getattr(store, "uses_firestore", False):
        db = get_async_firestore()
        if not db:
            return 0
        n = 0
        async for _ in db.collection(SESSIONS_COLLECTION).stream():
            n += 1
        return n
    memory = getattr(store, "_memory", {})
    return sum(1 for s in memory.values() if isinstance(s, Session))


def _card_contribution(card: ReportCard) -> dict[str, Any]:
    grade = (card.grade or "").strip().upper()
    c_or_worse = 1 if grade in {"C", "D", "F"} else 0

    tuition_gap = _tuition_gap_positive_usd(card)

    r = card.research
    cooked = _safe_int(r.overall_cooked_0_100)
    if cooked is None:
        cooked = _safe_int(r.ai_replacement_risk_0_100) or 50
    regret = max(0.0, min(5.0, cooked / 20.0))

    return {
        "total_cards": 1,
        "c_or_worse_count": c_or_worse,
        "tuition_in_shambles_usd": int(tuition_gap),
        "regret_sum_0_5": float(regret),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _render_aggregate_snapshot(
    *,
    total_cards: int,
    c_or_worse_count: int,
    tuition_in_shambles_usd: int,
    regret_sum_0_5: float,
    updated_at: str,
    people_talked_to_donald: int | None = None,
) -> dict[str, Any]:
    total = max(0, int(total_cards))
    people = max(0, int(people_talked_to_donald if people_talked_to_donald is not None else total))
    c_count = max(0, min(total, int(c_or_worse_count)))
    tuition = max(0, int(tuition_in_shambles_usd))
    regret_sum = _normalize_regret_sum_0_5(
        total_cards=total,
        regret_sum_0_5=regret_sum_0_5,
    )

    pct = round((c_count / total) * 100, 1) if total else 0.0
    regret = round(regret_sum / total, 1) if total else 0.0

    return {
        "total_cards": total,
        "c_or_worse_count": c_count,
        "regret_sum_0_5": round(regret_sum, 4),
        "degrees_cooked": total,
        "people_talked_to_donald": people,
        "c_or_worse_pct": pct,
        "tuition_in_shambles_usd": tuition,
        "regret_score_0_5": regret,
        "updated_at": updated_at,
        "display": {
            "degrees_cooked": f"{total:,}+",
            "people_talked_to_donald": f"{people:,}+",
            "c_or_worse_pct": f"{round(pct)}%",
            "tuition_in_shambles": _format_compact_usd(tuition),
            "regret_score": f"{regret:.1f}/5",
        },
    }


async def _read_metrics_snapshot() -> dict[str, Any] | None:
    db = get_async_firestore()
    if not db:
        return None
    doc = await db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    if not isinstance(data, dict):
        return None
    return data


async def _write_metrics_snapshot(snapshot: dict[str, Any]) -> None:
    db = get_async_firestore()
    if not db:
        return
    await db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID).set(snapshot)


def _rebuild_contrib_docs_sync(cards: list[ReportCard]) -> None:
    db = get_sync_firestore()
    if not db:
        return
    batch = db.batch()
    for i, card in enumerate(cards):
        contrib = _card_contribution(card)
        ref = db.collection(CONTRIB_COLLECTION).document(card.session_id)
        batch.set(ref, contrib)
        if (i + 1) % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()


def _apply_report_card_update_sync(session_id: str, report_card: ReportCard) -> dict[str, Any] | None:
    db = get_sync_firestore()
    if not db:
        return None

    try:
        from google.cloud import firestore as gcfirestore
    except Exception:
        return None

    metrics_ref = db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID)
    contrib_ref = db.collection(CONTRIB_COLLECTION).document(session_id)
    tx = db.transaction()

    @gcfirestore.transactional
    def _txn(transaction):
        metrics_snap = metrics_ref.get(transaction=transaction)
        contrib_snap = contrib_ref.get(transaction=transaction)
        metrics = metrics_snap.to_dict() or {}
        old = contrib_snap.to_dict() or {}
        new_contrib = _card_contribution(report_card)

        base_total = int(metrics.get("total_cards") or metrics.get("degrees_cooked") or 0)
        base_c = int(metrics.get("c_or_worse_count") or 0)
        if base_c == 0 and base_total > 0 and "c_or_worse_pct" in metrics:
            try:
                base_c = int(round((float(metrics.get("c_or_worse_pct") or 0.0) / 100.0) * base_total))
            except Exception:
                base_c = 0

        base_tuition = int(metrics.get("tuition_in_shambles_usd") or 0)
        base_regret_sum = float(metrics.get("regret_sum_0_5") or 0.0)
        if base_regret_sum == 0.0 and base_total > 0 and "regret_score_0_5" in metrics:
            try:
                base_regret_sum = float(metrics.get("regret_score_0_5") or 0.0) * base_total
            except Exception:
                base_regret_sum = 0.0
        base_regret_sum = _normalize_regret_sum_0_5(
            total_cards=base_total,
            regret_sum_0_5=base_regret_sum,
            regret_score_hint=metrics.get("regret_score_0_5"),
        )
        next_total = base_total + int(new_contrib["total_cards"]) - int(old.get("total_cards") or 0)
        next_c = base_c + int(new_contrib["c_or_worse_count"]) - int(old.get("c_or_worse_count") or 0)
        next_tuition = base_tuition + int(new_contrib["tuition_in_shambles_usd"]) - int(old.get("tuition_in_shambles_usd") or 0)
        next_regret_sum = base_regret_sum + float(new_contrib["regret_sum_0_5"]) - float(old.get("regret_sum_0_5") or 0.0)

        now_iso = datetime.now(timezone.utc).isoformat()
        base_people = int(metrics.get("people_talked_to_donald") or base_total)
        snapshot = _render_aggregate_snapshot(
            total_cards=max(0, next_total),
            people_talked_to_donald=max(0, base_people),
            c_or_worse_count=max(0, next_c),
            tuition_in_shambles_usd=max(0, next_tuition),
            regret_sum_0_5=max(0.0, next_regret_sum),
            updated_at=now_iso,
        )

        bootstrap_bits = {
            k: metrics[k]
            for k in (
                "bootstrap_fake_seed_done",
                "bootstrap_fake_seed_count",
                "bootstrap_fake_seeded_at",
            )
            if k in metrics
        }
        payload = {**snapshot, **bootstrap_bits}
        transaction.set(metrics_ref, payload, merge=True)
        transaction.set(contrib_ref, new_contrib)
        return payload

    return _txn(tx)


async def apply_report_card_update_async(session_id: str, report_card: ReportCard) -> dict[str, Any] | None:
    return await asyncio.to_thread(_apply_report_card_update_sync, session_id, report_card)


def apply_report_card_update_sync(session_id: str, report_card: ReportCard) -> dict[str, Any] | None:
    return _apply_report_card_update_sync(session_id, report_card)


def apply_report_card_update_memory(store, session_id: str, report_card: ReportCard) -> dict[str, Any]:
    contribs = getattr(store, "_metrics_contrib", None)
    if not isinstance(contribs, dict):
        contribs = {}
        setattr(store, "_metrics_contrib", contribs)

    snapshot = getattr(store, "_metrics_snapshot", None)
    if not isinstance(snapshot, dict):
        snapshot = _render_aggregate_snapshot(
            total_cards=0,
            people_talked_to_donald=0,
            c_or_worse_count=0,
            tuition_in_shambles_usd=0,
            regret_sum_0_5=0.0,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    old = contribs.get(session_id) or {
        "total_cards": 0,
        "c_or_worse_count": 0,
        "tuition_in_shambles_usd": 0,
        "regret_sum_0_5": 0.0,
    }
    new = _card_contribution(report_card)
    current_people = int(snapshot.get("people_talked_to_donald") or 0)

    next_snapshot = _render_aggregate_snapshot(
        total_cards=int(snapshot.get("total_cards") or 0) + int(new["total_cards"]) - int(old.get("total_cards") or 0),
        people_talked_to_donald=max(0, current_people),
        c_or_worse_count=int(snapshot.get("c_or_worse_count") or 0) + int(new["c_or_worse_count"]) - int(old.get("c_or_worse_count") or 0),
        tuition_in_shambles_usd=int(snapshot.get("tuition_in_shambles_usd") or 0)
        + int(new["tuition_in_shambles_usd"])
        - int(old.get("tuition_in_shambles_usd") or 0),
        regret_sum_0_5=float(snapshot.get("regret_sum_0_5") or 0.0)
        + float(new["regret_sum_0_5"])
        - float(old.get("regret_sum_0_5") or 0.0),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    contribs[session_id] = new
    setattr(store, "_metrics_snapshot", next_snapshot)
    return next_snapshot


async def recompute_public_metrics(store) -> dict[str, Any]:
    cards = await _collect_report_cards(store)
    people_count = await _count_sessions(store)
    snapshot = _compute_from_cards(cards, people_count=people_count)
    if getattr(store, "uses_firestore", False):
        await _write_metrics_snapshot(snapshot)
        await asyncio.to_thread(_rebuild_contrib_docs_sync, cards)
    else:
        setattr(store, "_metrics_snapshot", snapshot)
        setattr(store, "_metrics_contrib", {c.session_id: _card_contribution(c) for c in cards})
    return snapshot


async def get_public_metrics(store) -> dict[str, Any]:
    people_count = await _count_sessions(store)
    if not getattr(store, "uses_firestore", False):
        mem_snap = getattr(store, "_metrics_snapshot", None)
        if isinstance(mem_snap, dict):
            canonical = _snapshot_to_canonical(mem_snap)
            canonical["people_talked_to_donald"] = max(0, int(people_count))
            canonical.setdefault("display", {})
            canonical["display"]["people_talked_to_donald"] = f"{max(0, int(people_count)):,}+"
            setattr(store, "_metrics_snapshot", canonical)
            return canonical
    snap = await _read_metrics_snapshot()
    if isinstance(snap, dict):
        canonical = _snapshot_to_canonical(snap)
        canonical["people_talked_to_donald"] = max(0, int(people_count))
        canonical.setdefault("display", {})
        canonical["display"]["people_talked_to_donald"] = f"{max(0, int(people_count)):,}+"
        # Self-heal legacy snapshots in Firestore when canonical values changed.
        if canonical != snap:
            await _write_metrics_snapshot(canonical)
        return canonical
    return await recompute_public_metrics(store)


def _make_fake_session() -> Session:
    degrees = [
        "Business Administration",
        "Psychology",
        "Communications",
        "Computer Science",
        "Economics",
        "Marketing",
        "English",
        "Biology",
        "Political Science",
    ]
    schools = [
        "State University",
        "City College",
        "Northern Tech",
        "Westbridge University",
        "Metro Institute",
        "Kingsford University",
    ]
    jobs = [
        "Marketing Coordinator",
        "Data Analyst",
        "Operations Associate",
        "Junior Developer",
        "Account Manager",
        "HR Specialist",
        "Student",
    ]
    regions = [("United States", "USD"), ("United Kingdom", "GBP"), ("Germany", "EUR")]

    region, cc = random.choice(regions)
    degree = random.choice(degrees)
    school = random.choice(schools)
    job = random.choice(jobs)
    grad_year = random.randint(2012, 2026)
    salary = random.randint(35_000, 140_000) if job != "Student" else None
    years = random.randint(0, 12)

    est_tuition = random.randint(28_000, 160_000)
    invested = int(est_tuition * random.uniform(1.25, 2.8))
    gap = max(0, invested - est_tuition)
    ai = random.randint(38, 95)
    cooked = random.randint(max(40, ai - 8), min(100, ai + 10))

    if cooked >= 80:
        grade, score = "F", random.randint(18, 34)
    elif cooked >= 65:
        grade, score = "D", random.randint(35, 49)
    elif cooked >= 50:
        grade, score = "C", random.randint(50, 64)
    elif cooked >= 35:
        grade, score = "B", random.randint(65, 79)
    else:
        grade, score = "A", random.randint(80, 96)

    profile = UserProfile(
        name=f"User-{uuid.uuid4().hex[:6]}",
        degree=degree,
        university=school,
        graduation_year=grad_year,
        current_job=job,
        current_company="" if job == "Student" else "Sample Co",
        salary=salary,
        years_experience=years,
        country_or_region=region,
        currency_code=cc,
        tuition_paid=est_tuition,
        tuition_is_total=True,
        source="fake_seed",
    )
    research = ResearchData(
        currency_code=cc,
        avg_salary_for_degree=random.randint(42_000, 110_000),
        avg_salary_for_role=random.randint(40_000, 120_000),
        median_salary_for_role=random.randint(38_000, 115_000),
        salary_range_low=random.randint(28_000, 70_000),
        salary_range_high=random.randint(75_000, 185_000),
        estimated_tuition=est_tuition,
        tuition_if_invested=invested,
        tuition_opportunity_gap=gap,
        degree_roi_rank=f"{random.randint(40, 390)}/400",
        job_market_trend=random.choice(["growing", "flat", "shrinking"]),
        unemployment_rate_pct=round(random.uniform(2.1, 8.9), 1),
        job_openings_estimate=random.randint(12_000, 360_000),
        ai_replacement_risk_0_100=ai,
        ai_risk_reasoning="Synthetic seeded data for homepage metrics.",
        overall_cooked_0_100=cooked,
        safeguard_tips=[
            "Own measurable outcomes, not just task execution.",
            "Use AI tools weekly on real deliverables.",
            "Build a visible portfolio of before/after impact.",
        ],
        honest_take="Synthetic seeded report for dashboard metrics.",
    )
    report_card = ReportCard(
        session_id=str(uuid.uuid4()),
        grade=grade,
        grade_score=score,
        profile=profile,
        research=research,
        roast_quote="",
    )
    return Session(
        session_id=report_card.session_id,
        profile=profile,
        research=research,
        report_card=report_card,
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 200)),
        voice_activity=[],
    )


def _seed_firestore_sync(count: int) -> int:
    db = get_sync_firestore()
    if not db:
        return 0

    inserted = 0
    batch = db.batch()
    for i in range(count):
        session = _make_fake_session()
        ref = db.collection(SESSIONS_COLLECTION).document(session.session_id)
        batch.set(ref, _session_to_firestore_doc(session))
        inserted += 1
        if (i + 1) % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    return inserted


async def seed_fake_sessions(store, count: int = 200) -> tuple[int, bool]:
    n = max(1, min(5000, int(count)))

    if getattr(store, "uses_firestore", False):
        db = get_async_firestore()
        if not db:
            return (0, False)
        doc_ref = db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID)
        existing = await doc_ref.get()
        data = existing.to_dict() or {}
        if bool(data.get("bootstrap_fake_seed_done")):
            return (0, True)
        seeded = await asyncio.to_thread(_seed_firestore_sync, n)
        await doc_ref.set(
            {
                "bootstrap_fake_seed_done": True,
                "bootstrap_fake_seed_count": seeded,
                "bootstrap_fake_seeded_at": datetime.now(timezone.utc).isoformat(),
            },
            merge=True,
        )
        return (seeded, False)

    memory = getattr(store, "_memory", None)
    if not isinstance(memory, dict):
        return (0, False)
    if bool(getattr(store, "_bootstrap_fake_seed_done", False)):
        return (0, True)
    for _ in range(n):
        s = _make_fake_session()
        memory[s.session_id] = s
    setattr(store, "_bootstrap_fake_seed_done", True)
    return (n, False)
