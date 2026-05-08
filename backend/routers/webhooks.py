import asyncio
import io
import json
from email.policy import default
import os
from datetime import datetime, timezone

import structlog
import httpx
import pdfplumber
from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.services.firecrawl_service import run_research, resolve_research_query_plan
from backend.services.money_locale import normalize_currency_code
from backend.services.research_concurrency import (
    acquire_research_lease,
    release_lease_async,
)
from backend.services.research_outcome import (
    apply_cooked_components,
    grade_and_report_card,
    tuition_invested_for_api as _tuition_invested_for_api,
)
from backend.models import InternshipProfile, ReportCard, ResearchData, UserProfile
from backend.services.internship_research_service import run_internship_research
from backend.session_id import ensure_session_id

router = APIRouter()
logger = structlog.get_logger(__name__)

VOICE_RESEARCH_DEADLINE_SEC = float(os.getenv("VOICE_RESEARCH_DEADLINE_SEC", "270"))
VOICE_SESSION_MAX_SECONDS = int((os.getenv("VOICE_SESSION_MAX_SECONDS") or "180").strip())


def _profile_blurb(p: UserProfile) -> str:
    parts = [p.degree or "—", p.university or "—", p.current_job or "—"]
    return " · ".join(parts)


def _voice_research_profile_errors(p: UserProfile) -> str | None:
    """Light validation so the agent gets a spoken retry message."""
    if not (p.degree or "").strip():
        return "Missing degree — ask what they studied, then call research_degree again."
    if not (p.university or "").strip():
        return "Missing school or university — ask where they studied, then call research_degree again."
    if not (p.current_job or "").strip():
        return (
            "Missing current situation — ask their job title, student status, or what they're aiming for, "
            "then call research_degree again."
        )
    return None


def _internship_profile_errors(p: InternshipProfile) -> str | None:
    """Light validation for the internship voice flow."""
    if not (p.major or "").strip():
        return "Missing major — ask what they're studying, then call research_internship again."
    if not (p.university or "").strip():
        return "Missing university — ask where they study, then call research_internship again."
    if not p.target_companies:
        return "Missing target companies — ask which companies they're targeting, then call research_internship again."
    return None


def _truncate(s: str, n: int = 220) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _session_age_seconds(created_at: datetime) -> int:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return int((datetime.now(timezone.utc) - created_at).total_seconds())


def _voice_time_limit_payload() -> dict:
    return {
        "error": "Voice time limit reached for today (3 minutes max).",
        "research_complete": False,
        "agent_note": (
            "Daily voice limit reached. Apologize in one sentence and ask the user to come back tomorrow."
        ),
        "come_back_tomorrow": True,
    }


def _voice_research_started_payload(p: UserProfile, queries: list[str]) -> dict:
    return {
        "step": "research_started",
        "note": "Hang tight — we're checking salaries, tuition, and job-market signals for your roast.",
        "query_count": len(queries),
        "queries": queries,
        "profile": {
            "degree": p.degree,
            "university": p.university,
            "graduation_year": p.graduation_year,
            "current_job": p.current_job,
            "currency_code": p.currency_code,
            "country_or_region": p.country_or_region,
            "tuition_paid": p.tuition_paid,
            "tuition_is_total": p.tuition_is_total,
        },
    }


def _voice_research_complete_payload(research: ResearchData, grade: str, score: int) -> dict:
    hits = research.search_hit_counts or []
    total_hits = sum(hits) if hits else 0
    return {
        "step": "research_complete",
        "grade": grade,
        "grade_score": score,
        "currency_code": research.currency_code,
        "query_count": len(research.search_queries),
        "total_snippet_hits": total_hits,
        "hits_per_query": hits,
        "queries": research.search_queries,
        "key_numbers": {
            "avg_salary_for_degree": research.avg_salary_for_degree,
            "avg_salary_for_role": research.avg_salary_for_role,
            "median_salary_for_role": research.median_salary_for_role,
            "estimated_tuition": research.estimated_tuition,
            "tuition_web_estimate": research.tuition_web_estimate,
            "tuition_if_invested": _tuition_invested_for_api(research),
            "ai_replacement_risk_0_100": research.ai_replacement_risk_0_100,
            "near_term_ai_risk_0_100": research.near_term_ai_risk_0_100,
            "career_market_stress_0_100": research.career_market_stress_0_100,
            "financial_roi_stress_0_100": research.financial_roi_stress_0_100,
            "overall_cooked_0_100": research.overall_cooked_0_100,
            "job_market_trend": research.job_market_trend,
        },
        "sources": [s.model_dump() for s in research.sources[:12]],
        "named_sources": research.named_sources[:12],
    }


class WebhookRequest(BaseModel):
    session_id: str


class ResearchProfilePayload(BaseModel):
    """Inline profile for voice (degree roast) — not read from session store."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = ""
    degree: str = ""
    university: str = ""
    graduation_year: int = 0
    current_job: str = ""
    current_company: str = ""
    salary: int | None = None
    years_experience: int | None = Field(None, alias="yearsExperience")
    country_or_region: str = Field("", alias="countryOrRegion")
    currency_code: str = Field("USD", alias="currencyCode")
    tuition_paid: int | None = Field(None, alias="tuitionPaid")
    tuition_is_total: bool = Field(True, alias="tuitionIsTotal")
    source: str = "voice"

    @field_validator("currency_code", mode="before")
    @classmethod
    def _normalize_currency_code(cls, v: object) -> str:
        if v is None or v == "":
            return "USD"
        return normalize_currency_code(str(v).strip())

    @field_validator("country_or_region", mode="before")
    @classmethod
    def _strip_country(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("tuition_paid", mode="before")
    @classmethod
    def _coerce_tuition(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v if v > 0 else None
        s = str(v).strip().replace(",", "")
        if not s:
            return None
        try:
            n = int(float(s))
        except ValueError:
            return None
        return n if n > 0 else None

    @field_validator("tuition_is_total", mode="before")
    @classmethod
    def _coerce_tuition_is_total(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if v is None or v == "":
            return True
        s = str(v).strip().lower()
        if s in {"false", "0", "no", "annual", "per year", "yearly"}:
            return False
        return True

    def to_user_profile(self) -> UserProfile:
        return UserProfile(**self.model_dump(by_alias=False))


class InternshipProfilePayload(BaseModel):
    """Inline internship profile from voice — used by research_internship webhook."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    major: str = ""
    university: str = ""
    cgpa: float | None = None
    year_of_study: int | None = Field(None, alias="yearOfStudy")
    skills: list[str] = []
    courses: list[str] = []
    experience: str = ""
    languages_known: list[str] = Field([], alias="languagesKnown")
    target_companies: list[str] = Field([], alias="targetCompanies")
    country_or_region: str = Field("", alias="countryOrRegion")
    source: str = "voice"

    @field_validator("country_or_region", mode="before")
    @classmethod
    def _strip_country(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    def to_internship_profile(self) -> "InternshipProfile":
        return InternshipProfile(**self.model_dump(by_alias=False))


class ResearchDegreeWebhookRequest(BaseModel):
    session_id: str
    profile: ResearchProfilePayload


class InternshipWebhookRequest(BaseModel):
    session_id: str
    profile: InternshipProfilePayload


class SaveQuoteRequest(BaseModel):
    session_id: str
    quote: str


class UpdateUserProfileRequest(BaseModel):
    """Merge fields into the session profile (omit keys you are not setting). Voice agents call this after extracting answers, then call research_degree."""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    name: str | None = None
    degree: str | None = None
    university: str | None = None
    graduation_year: int | None = Field(None, alias="graduationYear")
    current_job: str | None = Field(None, alias="currentJob")
    current_company: str | None = Field(None, alias="currentCompany")
    salary: int | None = None
    years_experience: int | None = Field(None, alias="yearsExperience")
    country_or_region: str | None = Field(None, alias="countryOrRegion")
    currency_code: str | None = Field(None, alias="currencyCode")
    tuition_paid: int | None = Field(None, alias="tuitionPaid")
    tuition_is_total: bool | None = Field(None, alias="tuitionIsTotal")
    source: str | None = None


@router.post("/api/webhooks/get_user_profile")
async def webhook_get_profile(req: WebhookRequest, request: Request):
    ensure_session_id(req.session_id)
    store = request.app.state.store
    session = await store.get(req.session_id)
    if not session:
        return {"error": "Session not found"}
    if _session_age_seconds(session.created_at) > VOICE_SESSION_MAX_SECONDS:
        return _voice_time_limit_payload()
    p = session.profile
    await store.append_voice_activity(
        req.session_id,
        event="webhook_get_user_profile",
        title="Profile loaded",
        detail=_profile_blurb(p),
        data={
            "degree": p.degree,
            "university": p.university,
            "graduation_year": p.graduation_year,
            "current_job": p.current_job,
        },
    )
    return {
        "name": p.name,
        "degree": p.degree,
        "university": p.university,
        "graduation_year": p.graduation_year,
        "current_job": p.current_job,
        "current_company": p.current_company,
        "salary": p.salary,
        "years_experience": p.years_experience,
        "country_or_region": p.country_or_region,
        "currency_code": p.currency_code,
    }


@router.post("/api/webhooks/update_user_profile")
async def webhook_update_profile(req: UpdateUserProfileRequest, request: Request):
    ensure_session_id(req.session_id)
    store = request.app.state.store
    patch = req.model_dump(exclude={"session_id"}, exclude_unset=True)
    session = await store.get(req.session_id)
    if not session:
        return {"error": "Session not found", "ok": False}
    if _session_age_seconds(session.created_at) > VOICE_SESSION_MAX_SECONDS:
        return _voice_time_limit_payload()
    if not await store.patch_profile(req.session_id, patch):
        return {"error": "Session not found", "ok": False}
    session = await store.get(req.session_id)
    if not session:
        return {"error": "Session not found", "ok": False}
    p = session.profile
    keys = ", ".join(sorted(patch.keys())) if patch else "(no profile fields — agent may have skipped tool args or used wrong keys)"
    await store.append_voice_activity(
        req.session_id,
        event="webhook_update_user_profile",
        title="Profile updated from voice" if patch else "Profile merge (empty patch)",
        detail=keys,
        data=patch if patch else None,
    )
    return {
        "ok": True,
        "name": p.name,
        "degree": p.degree,
        "university": p.university,
        "graduation_year": p.graduation_year,
        "current_job": p.current_job,
        "current_company": p.current_company,
        "salary": p.salary,
        "years_experience": p.years_experience,
        "country_or_region": p.country_or_region,
        "currency_code": p.currency_code,
        "source": p.source,
    }


@router.post("/api/webhooks/research_internship")
async def webhook_internship_research(req: InternshipWebhookRequest, request: Request):
    ensure_session_id(req.session_id)
    store = request.app.state.store
    session = await store.get(req.session_id)
    if not session:
        return {
            "error": "Session not found",
            "research_complete": False,
            "agent_note": "Research did not run — session missing. Ask the user to restart the call from the app.",
        }
    if _session_age_seconds(session.created_at) > VOICE_SESSION_MAX_SECONDS:
        return _voice_time_limit_payload()

    p = req.profile.to_internship_profile()
    if err := _internship_profile_errors(p):
        return {
            "error": err,
            "research_complete": False,
            "agent_note": err,
        }

    allowed, retry_after, detail, lease = await acquire_research_lease(request, req.session_id)
    if not allowed:
        retry_hint = f" Try again in about {retry_after} seconds." if retry_after > 0 else ""
        message = detail or "Research is already running for your session. Please wait for it to finish."
        return {
            "error": f"{message}{retry_hint}",
            "research_complete": False,
            "agent_note": "Research is currently busy. Ask the user to wait briefly, then retry research_internship.",
        }

    await store.append_voice_activity(
        req.session_id,
        event="webhook_research_started",
        title="Researching your internship targets",
        detail=(
            f"Checking {len(p.target_companies)} companies — can take a minute. "
            "Stay on this tab; the agent will pick up when it's done."
        ),
        data={"companies": p.target_companies, "major": p.major},
    )

    try:
        try:
            result = await asyncio.wait_for(
                run_internship_research(p),
                timeout=VOICE_RESEARCH_DEADLINE_SEC,
            )
        except asyncio.TimeoutError:
            logger.error(
                "research_internship_timeout",
                deadline_sec=VOICE_RESEARCH_DEADLINE_SEC,
                session_prefix=req.session_id[:8],
            )
            return {
                "error": (
                    f"Research timed out after {int(VOICE_RESEARCH_DEADLINE_SEC)} seconds. "
                    "Try again, or check your FIRECRAWL_API_KEY / network."
                ),
                "research_complete": False,
                "agent_note": (
                    "Research did not finish in time — do not roast with made-up numbers. "
                    "Apologize briefly and offer to retry research_internship."
                ),
            }
    finally:
        await release_lease_async(request, lease)

    await store.append_voice_activity(
        req.session_id,
        event="webhook_research_complete",
        title="Internship research done",
        detail=f"Readiness score: {result.get('overall_readiness_score', 0)}/100",
        data=result,
    )

    return {
        "research_complete": True,
        "agent_note": (
            "Pipeline finished. Use ALL fields below for the roast — start immediately, "
            "do NOT ask the user to confirm data loaded. "
            "Go company-by-company through company_verdicts. "
            "End Phase 3 with honest_take and overall_readiness_score. "
            "Phase 4: walk through tips in order. Then save_roast_quote."
        ),
        **result,
    }



@router.post("/api/parse-cv")
async def parse_cv(file: UploadFile = File(...)):
    """Extract internship profile data from an uploaded CV PDF."""
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported."}

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        return {"error": "PDF too large — keep it under 8 MB."}

    text = ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.warning("pdf_parse_failed", error=str(e))
        return {"error": "Could not read PDF. Try a different file."}

    text = text.strip()
    if not text:
        return {"error": "No text found in PDF — try a non-scanned file."}

    snippet = text[:5000]

    groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not groq_api_key:
        return {"error": "GROQ_API_KEY not configured on server."}

    extraction_prompt = (
        "Extract the following details from this CV/resume text and return ONLY a valid JSON object.\n"
        "If a field is not found, use null for numbers and empty string/array for text.\n\n"
        "Fields to extract:\n"
        "- major: their field of study / degree programme (string)\n"
        "- university: name of their university or college (string)\n"
        "- cgpa: CGPA or GPA as a decimal number e.g. 3.7 (number or null)\n"
        "- year_of_study: which year they are in e.g. 2 for second year (integer or null)\n"
        "- skills: list of technical skills, tools, languages (array of strings)\n"
        "- courses: relevant courses or modules listed (array of strings)\n"
        "- experience: brief summary of any internships, projects, or work experience (string)\n"
        "- languages_known: programming or spoken languages they know (array of strings)\n"
        "- country_or_region: country or region they are based in (string)\n\n"
        f"CV TEXT:\n{snippet}\n\n"
        "Return ONLY the JSON object, no markdown, no explanation."
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.1,
            max_tokens=800,
        )
        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()
        profile_data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("cv_parse_json_error", error=str(e))
        return {"error": "CV parsing returned invalid data — try again."}
    except Exception as e:
        logger.warning("cv_parse_groq_error", error=str(e))
        return {"error": f"AI extraction failed: {str(e)[:120]}"}

    return {"ok": True, "profile": profile_data}


@router.post("/api/internship")
async def internship_direct(profile: InternshipProfile):
    """
    Sessionless endpoint — takes an InternshipProfile directly and runs the full roast pipeline.
    Used by the static HTML frontend (no ElevenLabs session required).
    """
    err = _internship_profile_errors(profile)
    if err:
        return {"error": err}
    result = await run_internship_research(profile)
    return result

@router.post("/api/speak")
async def speak_roast(request: Request):
    """
    Proxy ElevenLabs TTS — keeps the API key server-side.
    Accepts JSON: {"text": "..."} — returns audio/mpeg.
    """
    from fastapi.responses import Response as FastAPIResponse

    body = await request.json()
    text = (body.get("text") or "").strip()[:1800]  # cap to save chars
    if not text:
        return {"error": "No text provided"}

    xi_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not xi_key:
        return {"error": "ELEVENLABS_API_KEY not configured on server."}

    # Default: "Adam" — ElevenLabs built-in premade voice, works on free tier.
    # Override with any premade voice ID via ELEVENLABS_VOICE_ID in .env
    # Free-tier premade options: Adam=pNInz6obpgDQGcFmaJgB, Josh=TxGEqnHWrfWFTfGW9XjX,
    #   Sam=yoZ06aMxZJJ28mfd3POQ, Rachel=21m00Tcm4TlvDq8ikWAM, Bella=EXAVITQu4vr4xnSDxMaL
    # Library/shared voices (e.g. vgOO1n3...) require a paid ElevenLabs plan.
    voice_id = (os.getenv("ELEVENLABS_VOICE_ID") or "pNInz6obpgDQGcFmaJgB").strip()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": xi_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.35,
                        "similarity_boost": 0.8,
                        "style": 0.45,
                        "use_speaker_boost": True,
                    },
                },
            )
        if resp.status_code != 200:
            logger.warning("elevenlabs_tts_error", status=resp.status_code, body=resp.text[:200])
            return {"error": f"ElevenLabs error {resp.status_code}: {resp.text[:120]}"}

        return FastAPIResponse(content=resp.content, media_type="audio/mpeg")

    except Exception as e:
        logger.warning("elevenlabs_tts_exception", error=str(e))
        return {"error": f"TTS failed: {str(e)[:120]}"}


# ── Company Suggestions ──────────────────────────────────────────────────────

class SuggestCompaniesRequest(BaseModel):
    major: str = ""
    university: str = ""
    cgpa: float | None = None
    year_of_study: int | None = None
    skills: list[str] = []
    country_or_region: str = ""
    experience: str = ""


@router.post("/api/suggest-companies")
async def suggest_companies(req: SuggestCompaniesRequest):
    """Return 9 company suggestions tailored to the student's profile."""
    groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not groq_key:
        return {"error": "GROQ_API_KEY not configured."}

    skills_str = ", ".join(req.skills[:12]) if req.skills else "not specified"
    cgpa_str = str(req.cgpa) if req.cgpa else "not provided"
    region_str = req.country_or_region or "unspecified region"

    prompt = f"""You are a career advisor for university students seeking internships.
Given this student profile, suggest 9 companies that are realistic and well-matched.
Mix tiers: ~3 reach (top-tier), ~4 target (realistic), ~2 safety (very attainable).

Profile:
- Major: {req.major or 'not specified'}
- University: {req.university or 'not specified'}
- CGPA: {cgpa_str}
- Year: {req.year_of_study or 'not specified'}
- Skills: {skills_str}
- Region/Country: {region_str}
- Experience: {req.experience[:200] if req.experience else 'none listed'}

Rules:
- Suggest companies that actually hire interns in the student's field
- Prefer companies with a presence/hiring in {region_str}
- Include a healthy mix of big tech, mid-size product companies, and startups
- Be honest — don't suggest companies way out of reach without flagging it
- Keep reasons brutally short (max 10 words)

Respond ONLY with valid JSON — no explanation, no markdown:
{{
  "suggestions": [
    {{"name": "Company Name", "tier": "reach|target|safety", "reason": "why it fits in 10 words or less"}},
    ...
  ]
}}"""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens": 600,
                    "response_format": {"type": "json_object"},
                },
            )
        if resp.status_code != 200:
            return {"error": f"Groq error {resp.status_code}"}
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return {"suggestions": parsed.get("suggestions", [])}
    except Exception as e:
        logger.warning("suggest_companies_error", error=str(e))
        return {"error": str(e)[:120]}
