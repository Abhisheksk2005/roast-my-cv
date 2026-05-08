"""Sum tuition opportunity gaps from raw Firestore session docs (not public_metrics)."""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    from backend.database import get_sync_firestore
    from backend.models import ReportCard
    from backend.services.public_metrics_service import (
        SESSIONS_COLLECTION,
        _tuition_gap_positive_usd,
    )

    p = argparse.ArgumentParser(description="Sum tuition gaps from session report_card payloads only.")
    p.add_argument("--verbose", action="store_true", help="Print per-session gaps")
    args = p.parse_args()

    db = get_sync_firestore()
    if not db:
        raise SystemExit(
            "Firestore not configured (set GOOGLE_CLOUD_PROJECT / credentials). "
            "Cannot read sessions directly."
        )

    total = 0
    with_card = 0
    skipped_validate = 0
    for doc in db.collection(SESSIONS_COLLECTION).stream():
        data = doc.to_dict() or {}
        raw = data.get("report_card")
        if not isinstance(raw, dict):
            continue
        try:
            card = ReportCard.model_validate(raw)
        except Exception:
            skipped_validate += 1
            continue
        gap = _tuition_gap_positive_usd(card)
        total += gap
        with_card += 1
        if args.verbose and gap:
            print(f"{doc.id[:8]}…  +{gap:,}  ({card.profile.degree[:40] if card.profile.degree else '?'})")

    print("---")
    print(f"Sessions with valid report_card: {with_card}")
    if skipped_validate:
        print(f"Skipped (invalid report_card shape): {skipped_validate}")
    print(f"TOTAL tuition gap sum: {total:,}")


if __name__ == "__main__":
    main()
