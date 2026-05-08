/**
 * - If NEXT_PUBLIC_API_URL is unset: demo mode (mocks); server-side fallbacks use INTERNAL_API_URL.
 * - If it points at the same origin as this Next app (e.g. you pasted your ngrok frontend URL), use
 *   same-origin `/api/*` so next.config rewrites proxy to FastAPI (otherwise POST /api/session 404s on Next).
 * - Otherwise: direct to that backend URL.
 */
function resolveApiBase(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  const serverFallback = (process.env.INTERNAL_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

  if (!raw) {
    return typeof window === "undefined" ? serverFallback : "";
  }

  let base = raw.replace(/\/$/, "");
  if (!/^https?:\/\//i.test(base)) {
    base = `http://${base}`;
  }

  if (typeof window !== "undefined") {
    try {
      if (new URL(base).origin === window.location.origin) {
        return "";
      }
    } catch {
      /* ignore */
    }
  }

  return base;
}

const API_URL = resolveApiBase();
const DEMO_MODE = !process.env.NEXT_PUBLIC_API_URL;

// ── Mock data for demo mode (no backend needed) ──

function mockSessionId() {
  return "demo-" + Math.random().toString(36).slice(2, 10);
}

const MOCK_REPORT_CARD = {
  session_id: "demo",
  grade: "D",
  grade_score: 38,
  profile: {
    name: "Demo User",
    degree: "Communications",
    university: "State University",
    graduation_year: 2021,
    current_job: "Marketing Coordinator",
    salary: 48000,
    years_experience: 3,
    country_or_region: "United States",
    currency_code: "USD",
  },
  research: {
    currency_code: "USD",
    avg_salary_for_degree: 52000,
    estimated_tuition: 95000,
    tuition_if_invested: 142000,
    tuition_opportunity_gap: 47000,
    degree_roi_rank: "312/400",
    job_market_trend: "shrinking",
    ai_replacement_risk_0_100: 72,
    near_term_ai_risk_0_100: 78,
    career_market_stress_0_100: 85,
    financial_roi_stress_0_100: 62,
    overall_cooked_0_100: 68,
    job_task_exposure: [
      {
        task: "Draft social and email copy",
        time_pct: 30,
        automation_score_0_100: 82,
        timeline_horizon: "now",
        reasoning: "First drafts and variants are already common LLM workflows.",
      },
      {
        task: "Stakeholder meetings & approvals",
        time_pct: 25,
        automation_score_0_100: 28,
        timeline_horizon: "longer",
        reasoning: "Trust and sign-off stay human for a long time.",
      },
    ],
    ai_risk_reasoning: "72% of marketing coordinator tasks — content drafting, reporting, campaign scheduling — overlap with what current LLMs and automation tools handle. 3 years of experience isn't deep enough specialization to offset that.",
    safeguard_tips: [
      "Own campaign outcomes (revenue, pipeline) not just the slide decks and calendar posts.",
      "Pick one AI workflow you actually ship with weekly — prompts, evals, review — so you become the person who automates the work, not the one replaced by it.",
      "Quarterly task audit: list what you do monthly and tag each as automate / augment / human-only.",
      "Build a public portfolio of before/after results where AI sped you up — proof you multiply output.",
    ],
    honest_take: "You paid $95k for comms; market averages for coordinators sit around $52k while that tuition could've compounded to ~$142k in the S&P. With ~72% task overlap with AI, own revenue outcomes—not slide decks.",
    methodology_note:
      "Numbers come from the pages linked below. AI condensed snippets into this card. S&P-style growth uses a long-run average when snippets had no clear rate.",
    named_sources: ["BLS", "Glassdoor", "Payscale"],
    sources: [
      { title: "Marketing specialists — Occupational Outlook", url: "https://www.bls.gov/ooh/", topic: "Marketing Coordinator average salary median salary 2026 BLS" },
      { title: "Marketing coordinator salary range", url: "https://www.glassdoor.com/", topic: "Marketing Coordinator salary range entry level senior 2026" },
    ],
  },
  roast_quote: "",
};

const MOCK_REVIEWS: PublicReview[] = [
  {
    review_id: "demo-review-1",
    session_id: "demo-1",
    quote: "$180k degree, AI writes better essays. The numbers broke me.",
    reviewer_name: "Sarah M.",
    degree: "English Lit",
    university: "NYU",
    grade: "D",
    grade_score: 35,
    overall_cooked_0_100: 74,
    ai_replacement_risk_0_100: 72,
    created_at: new Date().toISOString(),
  },
  {
    review_id: "demo-review-2",
    session_id: "demo-2",
    quote: "67% automation risk + 90s of salary truth. Unwell.",
    reviewer_name: "Marcus T.",
    degree: "Comms",
    university: "USC",
    grade: "F",
    grade_score: 22,
    overall_cooked_0_100: 82,
    ai_replacement_risk_0_100: 67,
    created_at: new Date().toISOString(),
  },
  {
    review_id: "demo-review-3",
    session_id: "demo-3",
    quote: "CS degree, low replace risk. I'll take it.",
    reviewer_name: "Priya K.",
    degree: "CS",
    university: "Georgia Tech",
    grade: "A",
    grade_score: 90,
    overall_cooked_0_100: 24,
    ai_replacement_risk_0_100: 26,
    created_at: new Date().toISOString(),
  },
];

// ── API functions (with demo fallback) ──

export async function createSession(profile: {
  name: string;
  degree: string;
  university: string;
  graduation_year: number;
  current_job: string;
  current_company?: string;
  salary?: number;
  years_experience?: number;
  source?: string;
}): Promise<{ session_id: string }> {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 400));
    return { session_id: mockSessionId() };
  }
  const res = await fetch(`${API_URL}/api/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  const data = await res.json().catch(() => ({} as Record<string, unknown>));
  if (!res.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : `Could not create session (HTTP ${res.status})`;
    throw new Error(detail);
  }
  return data as { session_id: string };
}

/** Empty session for voice: profile is not accumulated server-side; agent passes inline \`profile\` to \`research_degree\`. */
export function createVoiceSession(): Promise<{ session_id: string }> {
  return createSession({
    name: "",
    degree: "",
    university: "",
    graduation_year: 0,
    current_job: "",
    current_company: "",
    source: "voice",
  });
}

export async function getReportCard(sessionId: string) {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 500));
    return { ...MOCK_REPORT_CARD, session_id: sessionId };
  }
  const res = await fetch(`${API_URL}/api/report-card/${sessionId}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.report_card;
}

export type PublicReview = {
  review_id: string;
  session_id: string;
  quote: string;
  reviewer_name: string;
  degree: string;
  university: string;
  grade: string;
  grade_score: number;
  overall_cooked_0_100?: number | null;
  ai_replacement_risk_0_100?: number | null;
  created_at: string;
};

export async function getPublicReviews(limit = 20): Promise<PublicReview[]> {
  const safeLimit = Math.min(Math.max(limit, 1), 24);
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 200));
    return MOCK_REVIEWS.slice(0, safeLimit);
  }
  const res = await fetch(`${API_URL}/api/reviews?limit=${safeLimit}`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data.reviews) ? (data.reviews as PublicReview[]) : [];
}

export async function submitReview(input: {
  sessionId: string;
  quote: string;
  reviewerName?: string;
}): Promise<{ ok: boolean; review?: PublicReview; error?: string }> {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 350));
    return {
      ok: true,
      review: {
        review_id: `demo-review-${Date.now()}`,
        session_id: input.sessionId,
        quote: input.quote,
        reviewer_name: input.reviewerName?.trim() || "You",
        degree: MOCK_REPORT_CARD.profile.degree,
        university: MOCK_REPORT_CARD.profile.university,
        grade: MOCK_REPORT_CARD.grade,
        grade_score: MOCK_REPORT_CARD.grade_score,
        overall_cooked_0_100: MOCK_REPORT_CARD.research.overall_cooked_0_100,
        ai_replacement_risk_0_100: MOCK_REPORT_CARD.research.ai_replacement_risk_0_100,
        created_at: new Date().toISOString(),
      },
    };
  }
  try {
    const res = await fetch(`${API_URL}/api/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: input.sessionId,
        quote: input.quote,
        reviewer_name: input.reviewerName?.trim() || undefined,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { ok: false, error: (data.detail as string) || `HTTP ${res.status}` };
    }
    return { ok: true, review: data.review as PublicReview };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Network error" };
  }
}

export type PublicMetrics = {
  degrees_cooked: number;
  people_talked_to_donald: number;
  c_or_worse_pct: number;
  tuition_in_shambles_usd: number;
  regret_score_0_5: number;
  updated_at: string;
  display: {
    degrees_cooked: string;
    people_talked_to_donald: string;
    c_or_worse_pct: string;
    tuition_in_shambles: string;
    regret_score: string;
  };
};

export async function getPublicMetrics(): Promise<PublicMetrics> {
  const res = await fetch(`${API_URL}/api/public-metrics`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch metrics (${res.status})`);
  }
  const data = await res.json();
  return data.metrics as PublicMetrics;
}

export type VoiceActivityServerItem = {
  id: string;
  ts: string;
  event: string;
  title: string;
  detail: string;
  data?: Record<string, unknown> | null;
};

export type VoiceActivityPollResult = {
  ok: boolean;
  items: VoiceActivityServerItem[];
  error?: string;
  httpStatus?: number;
};

/** Poll while on voice call — webhook + pipeline steps from the API */
export async function fetchVoiceActivity(sessionId: string): Promise<VoiceActivityPollResult> {
  if (DEMO_MODE) return { ok: true, items: [] };
  try {
    const res = await fetch(`${API_URL}/api/session/${sessionId}/voice-activity`, { cache: "no-store" });
    let data: { items?: VoiceActivityServerItem[]; detail?: string } = {};
    try {
      data = await res.json();
    } catch {
      /* empty body */
    }
    if (!res.ok) {
      return {
        ok: false,
        items: [],
        error: typeof data.detail === "string" ? data.detail : res.statusText || `HTTP ${res.status}`,
        httpStatus: res.status,
      };
    }
    return { ok: true, items: Array.isArray(data.items) ? data.items : [] };
  } catch (e) {
    return {
      ok: false,
      items: [],
      error: e instanceof Error ? e.message : "Cannot reach API (is the backend running?)",
    };
  }
}

// ── CV Coach ──

export type CVFix = {
  original_text: string;
  suggested_text: string;
  severity: "critical" | "important" | "suggestion";
  section: string;
};

export type CVEducation = {
  degree: string;
  institution: string;
  year?: string;
};

export type CVExperienceEntry = {
  title: string;
  company: string;
  dates?: string;
  summary?: string;
};

export type CVSectionFeedback = {
  name: string;
  score_0_10?: number;
  summary?: string;
};

export type CVAnalysisResult = {
  candidate_name?: string;
  candidate_email?: string;
  candidate_phone?: string;
  candidate_location?: string;
  current_role?: string;
  current_company?: string;
  experience_years?: number;
  education?: CVEducation[];
  skills?: string[];
  experience_entries?: CVExperienceEntry[];
  cv_text?: string;
  overall_score_0_100: number;
  overall_summary: string;
  strengths: string[];
  top_actions: string[];
  sections?: CVSectionFeedback[];
  highlights: CVFix[];
  coaching_notes: string;
  file_name: string;
};

export async function uploadCV(
  file: File,
  sessionId?: string,
): Promise<{ analysis: CVAnalysisResult; session_id: string | null }> {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 1500));
    return { analysis: MOCK_CV_ANALYSIS, session_id: null };
  }
  const form = new FormData();
  form.append("file", file);
  const url = sessionId
    ? `${API_URL}/api/cv/upload?session_id=${encodeURIComponent(sessionId)}`
    : `${API_URL}/api/cv/upload`;
  const res = await fetch(url, { method: "POST", body: form });
  const data = await res.json().catch(() => ({} as Record<string, unknown>));
  if (!res.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `CV upload failed (HTTP ${res.status})`,
    );
  }
  return data as { analysis: CVAnalysisResult; session_id: string | null };
}

const MOCK_CV_ANALYSIS: CVAnalysisResult = {
  candidate_name: "Jane Doe",
  candidate_email: "jane@example.com",
  candidate_phone: "+1 555-0123",
  candidate_location: "New York, NY",
  current_role: "Marketing Coordinator",
  current_company: "Acme Corp",
  experience_years: 3,
  education: [
    { degree: "BA Communications", institution: "State University", year: "2021" },
  ],
  skills: ["Microsoft Office", "Teamwork", "Email Marketing", "Social Media"],
  experience_entries: [
    {
      title: "Marketing Coordinator",
      company: "Acme Corp",
      dates: "2021 – Present",
      summary: "Managed email campaigns and social media accounts.",
    },
    {
      title: "Marketing Intern",
      company: "StartupXYZ",
      dates: "2020 – 2021",
      summary: "Assisted with content creation and analytics reporting.",
    },
  ],
  cv_text:
    "Jane Doe\njane@example.com\n\nExperience\n- Helped with email marketing\n\nSkills\n- Microsoft Office\n- Teamwork\n",
  overall_score_0_100: 35,
  overall_summary:
    "Recruiter would spend 4 seconds on this. No numbers, no outcomes, no differentiation.",
  strengths: [
    "Clean chronological layout",
    "Contact info present and complete",
  ],
  top_actions: [
    "Generic objective wastes prime space → Replace with 2-line summary naming your niche and biggest win",
    "Zero metrics in experience bullets → Add follower growth %, open rates, revenue driven",
    "'Microsoft Office' and 'Teamwork' are filler → List real tools: HubSpot, GA, Hootsuite",
    "No achievements section → Add 2-3 quantified highlights above Experience",
  ],
  highlights: [
    {
      original_text: "Generic objective statement",
      suggested_text: "Write a 2-line professional summary with your niche + top result",
      severity: "critical",
      section: "Objective",
    },
    {
      original_text: "Experience bullets list duties not outcomes",
      suggested_text: "Add numbers: '40% follower growth', '$2M pipeline', '27% open rate'",
      severity: "important",
      section: "Experience",
    },
    {
      original_text: "'Helped with email marketing'",
      suggested_text: "Own it: 'Designed weekly campaigns for 15k subscribers'",
      severity: "critical",
      section: "Experience",
    },
    {
      original_text: "Skills section is filler words",
      suggested_text: "Replace with specific, searchable tools and certifications",
      severity: "important",
      section: "Skills",
    },
  ],
  coaching_notes:
    "Your CV reads like a job description, not a highlight reel. You listed duties instead of wins. One evening adding real numbers could take this from a 35 to a 70.",
  file_name: "demo_cv.pdf",
};

/** Browser → \`get_user_profile\` webhook (LinkedIn/manual sessions with stored profile). Voice flow does not use this. */
export async function webhookGetUserProfile(sessionId: string): Promise<{ ok: boolean; error?: string }> {
  if (DEMO_MODE) return { ok: true };
  try {
    const res = await fetch(`${API_URL}/api/webhooks/get_user_profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const t = await res.text();
      return { ok: false, error: t.slice(0, 200) || `HTTP ${res.status}` };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Network error" };
  }
}
