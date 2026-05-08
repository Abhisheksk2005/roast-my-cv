"""Celery application (broker: Redis)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from backend.logging_config import configure_logging

configure_logging()

from celery import Celery


def _broker_url() -> str:
    return (
        (os.getenv("CELERY_BROKER_URL") or "").strip()
        or (os.getenv("REDIS_URL") or "").strip()
        or "redis://localhost:6379/0"
    )


def _result_backend() -> str:
    return (os.getenv("CELERY_RESULT_BACKEND") or "").strip() or _broker_url()


celery_app = Celery(
    "donald",
    broker=_broker_url(),
    backend=_result_backend(),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    task_default_queue="donald",
    task_routes={"research.run_session": {"queue": "donald"}},
)

# Register @shared_task handlers
import backend.tasks.research_task  # noqa: E402, F401
