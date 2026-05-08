from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore import Client as SyncClient

from backend.models import CVAnalysis, Session, UserProfile, ResearchData, ReportCard, VoiceActivityItem
from backend.services.public_metrics_service import (
    apply_report_card_update_async,
    apply_report_card_update_sync,
)


COLLECTION = "sessions"


def _session_dict_to_model(session_id: str, data: dict[str, Any]) -> Session:
    profile = UserProfile.model_validate(data["profile"])
    research = ResearchData.model_validate(data["research"]) if data.get("research") else None
    report_card = ReportCard.model_validate(data["report_card"]) if data.get("report_card") else None
    cv_analysis = CVAnalysis.model_validate(data["cv_analysis"]) if data.get("cv_analysis") else None
    raw_created = data.get("created_at")
    if isinstance(raw_created, datetime):
        created_at = raw_created
    elif isinstance(raw_created, str):
        created_at = datetime.fromisoformat(raw_created.replace("Z", "+00:00"))
    elif raw_created is not None:
        ts_fn = getattr(raw_created, "timestamp", None)
        try:
            if callable(ts_fn):
                created_at = datetime.fromtimestamp(float(ts_fn()))
            else:
                created_at = datetime.now()
        except Exception:
            created_at = datetime.now()
    else:
        created_at = datetime.now()

    voice_raw = data.get("voice_activity") or []
    voice_activity: list[VoiceActivityItem] = []
    for item in voice_raw:
        if isinstance(item, dict):
            voice_activity.append(VoiceActivityItem.model_validate(item))

    return Session(
        session_id=session_id,
        profile=profile,
        research=research,
        report_card=report_card,
        cv_analysis=cv_analysis,
        created_at=created_at,
        voice_activity=voice_activity,
    )


def _session_to_firestore_doc(session: Session) -> dict[str, Any]:
    return {
        "profile": session.profile.model_dump(mode="json"),
        "research": session.research.model_dump(mode="json") if session.research else None,
        "report_card": session.report_card.model_dump(mode="json") if session.report_card else None,
        "cv_analysis": session.cv_analysis.model_dump(mode="json") if session.cv_analysis else None,
        "created_at": session.created_at,
        "voice_activity": [i.model_dump(mode="json") for i in session.voice_activity],
    }


class AsyncSessionRepository:
    def __init__(self, db: AsyncClient):
        self._db = db

    async def get(self, session_id: str) -> Session | None:
        doc = await self._db.collection(COLLECTION).document(session_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return _session_dict_to_model(session_id, data)

    async def create(self, profile: UserProfile) -> str:
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            profile=profile,
            created_at=datetime.now(),
        )
        await self._db.collection(COLLECTION).document(session_id).set(_session_to_firestore_doc(session))
        return session_id

    async def save(self, session: Session) -> None:
        await self._db.collection(COLLECTION).document(session.session_id).set(
            _session_to_firestore_doc(session)
        )

    async def update_research(self, session_id: str, research: ResearchData) -> None:
        session = await self.get(session_id)
        if not session:
            return
        session.research = research
        await self.save(session)

    async def update_report_card(self, session_id: str, report_card: ReportCard) -> None:
        session = await self.get(session_id)
        if not session:
            return
        session.report_card = report_card
        await self.save(session)
        await apply_report_card_update_async(session_id, report_card)

    async def update_cv_analysis(self, session_id: str, cv_analysis: CVAnalysis) -> None:
        session = await self.get(session_id)
        if not session:
            return
        session.cv_analysis = cv_analysis
        await self.save(session)

    async def update_roast_quote(self, session_id: str, quote: str) -> None:
        session = await self.get(session_id)
        if not session or not session.report_card:
            return
        session.report_card = session.report_card.model_copy(update={"roast_quote": quote})
        await self.save(session)

    async def patch_profile(self, session_id: str, updates: dict) -> bool:
        session = await self.get(session_id)
        if not session:
            return False
        allowed = set(UserProfile.model_fields.keys())
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return True
        session.profile = session.profile.model_copy(update=filtered)
        await self.save(session)
        return True

    async def append_voice_activity(
        self,
        session_id: str,
        *,
        event: str,
        title: str,
        detail: str = "",
        data: dict | None = None,
    ) -> None:
        session = await self.get(session_id)
        if not session:
            return
        session.voice_activity.append(
            VoiceActivityItem(event=event, title=title, detail=detail, data=data)
        )
        if len(session.voice_activity) > 120:
            session.voice_activity[:] = session.voice_activity[-120:]
        await self.save(session)


class SyncSessionRepository:
    """Sync Firestore client for Celery workers."""

    def __init__(self, db: SyncClient):
        self._db = db

    def get(self, session_id: str) -> Session | None:
        doc = self._db.collection(COLLECTION).document(session_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return _session_dict_to_model(session_id, data)

    def save(self, session: Session) -> None:
        self._db.collection(COLLECTION).document(session.session_id).set(
            _session_to_firestore_doc(session)
        )

    def update_research(self, session_id: str, research: ResearchData) -> None:
        session = self.get(session_id)
        if not session:
            return
        session.research = research
        self.save(session)

    def update_report_card(self, session_id: str, report_card: ReportCard) -> None:
        session = self.get(session_id)
        if not session:
            return
        session.report_card = report_card
        self.save(session)
        apply_report_card_update_sync(session_id, report_card)
