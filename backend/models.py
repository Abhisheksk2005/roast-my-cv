import uuid
from typing import Any

from pydantic import BaseModel, Field
from datetime import datetime


class VoiceActivityItem(BaseModel):
    """Append-only feed for voice UI (webhooks + optional client mirror)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: datetime = Field(default_factory=datetime.now)
    event: str
    title: str
    detail: str = ""
    data: dict[str, Any] | None = None


class ResearchSource(BaseModel):
    """One page or result used to build the report (from web search)."""

    title: str = ""
    url: str = ""
    topic: str = ""  # short label, e.g. which search theme this came from


class JobTaskExposure(BaseModel):
    """One concrete work task with time share and automation exposure (from Claude task decomposition)."""

    task: str = ""
    time_pct: int = 0  # ~% of workweek; server clamps
    automation_score_0_100: int = 50
    reasoning: str = ""
    timeline_horizon: str = "longer"  # now | 1_2_years | 3_5_years | longer


class UserProfile(BaseModel):
    name: str
    degree: str
    university: str
    graduation_year: int
    current_job: str
    current_company: str = ""
    salary: int | None = None
    years_experience: int | None = Field(
        default=None,
        description="Years in role or field; improves AI risk + safeguard tailoring.",
    )
    # Voice agent sets these when the user gives a region (e.g. UK + £60k → GBP).
    country_or_region: str = ""
    currency_code: str = Field(
        default="USD",
        description="ISO 4217: USD, GBP, EUR, etc. All salary/tuition integers use this currency.",
    )
    # Voice / forms: total degree cost the user states (major units of currency_code). Drives report tuition when set.
    tuition_paid: int | None = Field(
        default=None,
        description="User-reported total tuition/fees paid or projected (major units). Canonical when present.",
    )
    tuition_is_total: bool = Field(
        default=True,
        description="If False, tuition_paid is treated as annual — multiplied to approximate total.",
    )
    source: str = "manual"


class InternshipProfile(BaseModel):
    """Profile for the internship roast pipeline."""

    major: str = ""
    university: str = ""
    cgpa: float | None = None
    year_of_study: int | None = None
    skills: list[str] = []
    courses: list[str] = []
    experience: str = ""
    languages_known: list[str] = []
    target_companies: list[str] = []
    country_or_region: str = ""
    source: str = "voice"


class CompanyVerdict(BaseModel):
    """One company's verdict against the student's profile."""

    company: str = ""
    verdict: str = ""  # "Realistic" | "Reach" | "Be honest with yourself"
    reason: str = ""
    bright_spot: str = ""
    skill_gaps: list[str] = []
    one_fix: str = ""


class RecommendedCompany(BaseModel):
    """A company recommended based on the student's actual CV profile."""

    name: str = ""
    tier: str = ""  # reach | target | safety
    reason: str = ""  # Why this fits their specific profile


class InternshipResearchResult(BaseModel):
    """Output of the internship research pipeline."""

    overall_readiness_score: int = 0  # 0-100
    company_verdicts: list[CompanyVerdict] = []
    top_skill_gaps: list[str] = []
    bright_spots: list[str] = []
    tips: list[str] = []
    honest_take: str = ""
    voice_script: str = ""
    search_queries: list[str] = []
    recommended_companies: list[RecommendedCompany] = []


class ResearchData(BaseModel):
    currency_code: str = Field(
        default="USD",
        description="ISO 4217 for all monetary fields in this object.",
    )
    avg_salary_for_degree: int | None = None
    avg_salary_for_role: int | None = None
    median_salary_for_role: int | None = None
    salary_range_low: int | None = None
    salary_range_high: int | None = None
    estimated_tuition: int | None = None
    # When user supplied tuition_paid, this holds the web/LLM estimate for comparison (optional).
    tuition_web_estimate: int | None = None
    tuition_if_invested: int | None = None
    tuition_opportunity_gap: int | None = None
    degree_roi_rank: str | None = None
    job_market_trend: str | None = None
    unemployment_rate_pct: float | None = None
    job_openings_estimate: int | None = None
    raw_search_results: list[str] = []
    sources: list[ResearchSource] = Field(default_factory=list)
    named_sources: list[str] = Field(
        default_factory=list,
        description="Organizations named in snippets (e.g. BLS, Glassdoor), from AI extraction.",
    )
    methodology_note: str = ""
    search_queries: list[str] = Field(
        default_factory=list,
        description="Firecrawl search strings used for this run (voice activity UI).",
    )
    search_hit_counts: list[int] = Field(
        default_factory=list,
        description="Parallel to search_queries: raw result rows with text per query.",
    )

    # S&P 500 financial model
    sp500_annual_return_pct: float | None = None
    sp500_total_return_pct: float | None = None
    tuition_as_sp500_today: int | None = None
    years_since_graduation: int | None = None
    lifetime_earnings_estimate: int | None = None
    degree_premium_over_hs: int | None = None

    ai_replacement_risk_0_100: int | None = None
    ai_risk_reasoning: str = ""
    overall_cooked_0_100: int | None = None
    # Task decomposition (optional): when present, ai_replacement_risk_0_100 is time-weighted from tasks.
    job_task_exposure: list[JobTaskExposure] = Field(default_factory=list)
    near_term_ai_risk_0_100: int | None = Field(
        None,
        description="AI exposure in ~0–2y horizon from tasks with timeline now/1_2_years only.",
    )
    # Cooked meter components (higher = worse). overall_cooked blends these with AI risk.
    career_market_stress_0_100: int | None = Field(
        None,
        description="Job market / trajectory stress from trend + unemployment.",
    )
    financial_roi_stress_0_100: int | None = Field(
        None,
        description="Tuition vs index opportunity-cost stress.",
    )
    safeguard_tips: list[str] = []
    honest_take: str = ""


class ReportCard(BaseModel):
    session_id: str
    grade: str
    grade_score: int
    profile: UserProfile
    research: ResearchData
    roast_quote: str = ""


class PublicReview(BaseModel):
    """User-submitted testimonial snapshot derived from a generated report card."""

    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    quote: str
    reviewer_name: str
    degree: str
    university: str
    grade: str
    grade_score: int
    overall_cooked_0_100: int | None = None
    ai_replacement_risk_0_100: int | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class CVHighlight(BaseModel):
    """One specific issue found in the CV with the exact text to fix."""

    original_text: str = Field(
        ..., description="Exact substring from the CV that needs attention."
    )
    suggested_text: str = Field(
        ..., description="Replacement text (may be empty if the fix is 'remove this')."
    )
    reason: str = Field(
        ..., description="Why this change matters — one or two sentences."
    )
    severity: str = Field(
        default="suggestion",
        description="critical | important | suggestion",
    )
    section: str = Field(
        default="",
        description="Which CV section this belongs to (e.g. Summary, Experience, Skills).",
    )


class CVSectionFeedback(BaseModel):
    """Feedback for one logical section of the CV."""

    name: str = Field(..., description="Section heading as found in the CV.")
    score_0_10: int = Field(
        default=5, description="Quality score 0 (awful) – 10 (perfect)."
    )
    summary: str = Field(
        default="", description="One-paragraph assessment of this section."
    )
    highlights: list[CVHighlight] = Field(default_factory=list)


class CVEducation(BaseModel):
    """One education entry extracted from the CV."""

    degree: str = ""
    institution: str = ""
    year: str = ""


class CVExperienceEntry(BaseModel):
    """One work experience entry extracted from the CV."""

    title: str = ""
    company: str = ""
    dates: str = ""
    summary: str = ""


class CVAnalysis(BaseModel):
    """Full Claude analysis of an uploaded CV."""

    candidate_name: str = Field(default="", description="Name detected from the CV, if present.")
    candidate_email: str = Field(default="", description="Email from the CV.")
    candidate_phone: str = Field(default="", description="Phone from the CV.")
    candidate_location: str = Field(default="", description="Location from the CV.")
    current_role: str = Field(default="", description="Most recent job title.")
    current_company: str = Field(default="", description="Most recent employer.")
    experience_years: int = Field(default=0, description="Estimated years of experience.")
    education: list[CVEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="Key skills/tools extracted.")
    experience_entries: list[CVExperienceEntry] = Field(default_factory=list)
    cv_text: str = Field(default="", description="Extracted plain text of the CV.")
    overall_score_0_100: int = Field(default=50)
    overall_summary: str = Field(
        default="",
        description="2-3 sentence executive summary of the CV quality.",
    )
    strengths: list[str] = Field(default_factory=list)
    top_actions: list[str] = Field(
        default_factory=list,
        description="Prioritised list of the most impactful changes to make.",
    )
    sections: list[CVSectionFeedback] = Field(default_factory=list)
    highlights: list[CVHighlight] = Field(
        default_factory=list,
        description="All highlights across sections, flattened for easy rendering.",
    )
    coaching_notes: str = Field(
        default="",
        description="Extended coaching advice Donald can narrate.",
    )
    file_name: str = ""
    analyzed_at: datetime = Field(default_factory=datetime.now)


class Session(BaseModel):
    session_id: str
    profile: UserProfile
    research: ResearchData | None = None
    report_card: ReportCard | None = None
    cv_analysis: CVAnalysis | None = None
    created_at: datetime
    voice_activity: list[VoiceActivityItem] = Field(default_factory=list)
