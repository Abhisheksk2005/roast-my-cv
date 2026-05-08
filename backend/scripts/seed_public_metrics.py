from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed fake sessions and recompute public metrics.")
    p.add_argument("--count", type=int, default=200, help="How many fake sessions to seed (default: 200).")
    return p.parse_args()


async def _run(count: int) -> None:
    from backend.session_store import SessionStore
    from backend.services.public_metrics_service import (
        recompute_public_metrics,
        seed_fake_sessions,
    )

    store = SessionStore()
    seeded, already_seeded = await seed_fake_sessions(store, count)
    metrics = await recompute_public_metrics(store)

    if already_seeded:
        print("Fake bootstrap already applied before; no new fake sessions inserted.")
    else:
        print(f"Seeded sessions: {seeded}")
    print("Updated metrics:")
    print(f"- Degrees Cooked: {metrics['display']['degrees_cooked']}")
    print(f"- Got a C or Worse: {metrics['display']['c_or_worse_pct']}")
    print(f"- Tuition in Shambles: {metrics['display']['tuition_in_shambles']}")
    print(f"- Regret Score: {metrics['display']['regret_score']}")
    print(f"- Updated At: {metrics['updated_at']}")

    if not store.uses_firestore:
        print("Warning: Firestore is disabled/unconfigured; data was seeded in-memory only.")


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    args = _parse_args()
    asyncio.run(_run(args.count))


if __name__ == "__main__":
    main()
