"use client";

import { useConversation } from "@elevenlabs/react";
import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MicIcon, DonaldLogo } from "./icons";
import type { VoiceActivityRow } from "./VoiceActivityPanel";
import {
  VOICE_RESEARCH_CLIENT_DONE_TITLE,
  VOICE_RESEARCH_CLIENT_ERROR_TITLE,
  VOICE_RESEARCH_CLIENT_START_TITLE,
} from "@/lib/voiceActivityResearch";
import { isVoiceClientToolName } from "@/lib/voiceAgentTools";
import { uploadCV, type CVAnalysisResult } from "@/lib/api";

// ElevenLabs Client tool names + parameter list: `src/lib/voiceAgentTools.ts`
// If tools never run: ElevenLabs agent must use **Client** tools, not Webhooks -- see `prompts/ELEVENLABS_CLIENT_TOOLS_CHECKLIST.md`.

interface Props {
  sessionId: string;
  onComplete: () => void;
  /** Live SDK events (tool invocations, transcripts, connection) for the activity panel */
  onSdkActivity?: (row: VoiceActivityRow) => void;
  /** CV analysis pre-loaded before the call started (from the choose step). */
  preloadedCv?: CVAnalysisResult | null;
  /** Auto-start the voice call as soon as component mounts. */
  autoStart?: boolean;
  /** Upstream hook so page can render a dedicated CV section. */
  onCvAnalysis?: (analysis: CVAnalysisResult) => void;
}

function rid() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `live-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/** User-facing label when the platform runs an extra step (rare with client tools). */
function toolLine(toolName: string) {
  const labels: Record<string, string> = {
    research_degree: "Double-checking your story",
    save_roast_quote: "Saving a highlight for your report",
  };
  return labels[toolName] || "Quick extra step";
}

function userFacingErrorMessage(message: string): string {
  const m = (message || "").trim();
  if (!m) return "Something went wrong. Please try again.";
  if (/quota limit|exceeds your quota/i.test(m)) {
    return "Voice credits are exhausted right now. Please try again later.";
  }
  if (/daily voice limit|come back tomorrow|3-minute daily limit|time limit reached/i.test(m)) {
    return "You hit today's voice limit. Come back tomorrow for another roast.";
  }
  if (/missing\s+error_event|dynamic variables|agent config/i.test(m)) {
    return "Agent config mismatch. Refresh and retry. If it repeats, update the ElevenLabs agent variables.";
  }
  if (
    m.length > 140 ||
    /\bHTTP\b|401|403|404|500|502|503|ECONNREFUSED|Failed to fetch|NetworkError|JSON|session not found/i.test(m)
  ) {
    return "We couldn't finish that. Check your connection and try again.";
  }
  return m.length > 220 ? `${m.slice(0, 217)}\u2026` : m;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const USE_CONVAI_TOKEN = process.env.NEXT_PUBLIC_ELEVENLABS_USE_TOKEN === "true";
const BRANCH_ID = (process.env.NEXT_PUBLIC_ELEVENLABS_BRANCH_ID || "").trim();
const VOICE_SDK_DEBUG = process.env.NEXT_PUBLIC_VOICE_SDK_DEBUG === "true";
/** Structured console logging for local debugging (set NEXT_PUBLIC_VOICE_DEV_LOG=true). */
const VOICE_DEV_LOG = process.env.NEXT_PUBLIC_VOICE_DEV_LOG === "true";

/**
 * Sent as `sendUserMessage` after `research_internship` returns so the agent takes its next turn.
 * Prefix is stripped from the live activity feed (not shown as "You said").
 */
const APP_RESEARCH_DONE_SENTINEL = "__donald_app:research_ok__ ";
const APP_RESEARCH_DONE_NUDGE = `${APP_RESEARCH_DONE_SENTINEL}The research_degree tool already returned success with research_complete true. Speak now: begin your roast (Phase 3). Do not wait for the user to confirm.`;

const APP_CV_READY_SENTINEL = "__donald_app:cv_ready__ ";

function compactCvForVoice(a: CVAnalysisResult): string {
  const profile: string[] = [];
  if (a.candidate_name) profile.push(`NAME: ${a.candidate_name}`);
  if (a.current_role) profile.push(`CURRENT_ROLE: ${a.current_role}`);
  if (a.current_company) profile.push(`CURRENT_COMPANY: ${a.current_company}`);
  if (a.experience_years) profile.push(`EXPERIENCE_YEARS: ${a.experience_years}`);
  if (a.candidate_location) profile.push(`LOCATION: ${a.candidate_location}`);
  if (a.education?.length) {
    const edu = a.education.map((e) => `${e.degree} @ ${e.institution}${e.year ? ` (${e.year})` : ""}`).join("; ");
    profile.push(`EDUCATION: ${edu}`);
  }
  if (a.skills?.length) profile.push(`KEY_SKILLS: ${a.skills.slice(0, 10).join(", ")}`);
  if (a.experience_entries?.length) {
    const exp = a.experience_entries.slice(0, 3).map((e) => `${e.title} @ ${e.company}${e.dates ? ` (${e.dates})` : ""}`).join("; ");
    profile.push(`RECENT_ROLES: ${exp}`);
  }

  const fixes = (a.highlights || [])
    .slice(0, 5)
    .map((f) => `[${f.severity}/${f.section}] ${f.original_text} \u2192 ${f.suggested_text}`)
    .join("; ");

  return [
    "--- CANDIDATE PROFILE (from CV) ---",
    ...profile,
    "",
    "--- CV ANALYSIS ---",
    `CV_SCORE: ${a.overall_score_0_100}/100`,
    `VERDICT: ${a.overall_summary}`,
    `STRENGTHS: ${a.strengths.join(", ")}`,
    `FIXES: ${fixes}`,
    a.coaching_notes ? `DONALD_TAKE: ${a.coaching_notes}` : "",
  ]
    .filter((line) => line !== undefined)
    .join("\n");
}

function voiceDevJson(value: unknown, maxLen = 6000): string {
  try {
    const s = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    return s.length > maxLen ? `${s.slice(0, maxLen)}\n\u2026 [truncated ${s.length - maxLen} chars]` : s;
  } catch {
    return String(value);
  }
}

function voiceDevLog(category: string, message: string, data?: unknown) {
  if (!VOICE_DEV_LOG || typeof console === "undefined") return;
  const ts = new Date().toISOString();
  const prefix = `[Donald voice][${ts}][${category}] ${message}`;
  if (data !== undefined) {
    console.log(prefix, data);
  } else {
    console.log(prefix);
  }
}

/** Voice research can run many Firecrawl queries + Claude; must stay under ElevenLabs client-tool timeout. */
const RESEARCH_WEBHOOK_TIMEOUT_MS = 280_000;

async function postWebhook(
  path: string,
  body: unknown,
  options?: { timeoutMs?: number }
): Promise<string> {
  const timeoutMs = options?.timeoutMs;
  const ctrl = typeof timeoutMs === "number" ? new AbortController() : null;
  const timer =
    ctrl && timeoutMs
      ? setTimeout(() => ctrl.abort(), timeoutMs)
      : null;
  voiceDevLog("api", `POST ${API_URL}${path}`, { body: voiceDevJson(body, 2500), timeoutMs: timeoutMs ?? null });
  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl?.signal,
    });
    const text = await res.text();
    voiceDevLog("api", `Response ${path} HTTP ${res.status}`, {
      ok: res.ok,
      body: voiceDevJson(text, 8000),
    });
    if (!res.ok) {
      throw new Error(text.slice(0, 800) || `HTTP ${res.status}`);
    }
    return text || "{}";
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error(
        "Research is taking too long \u2014 the connection timed out. Check your API keys and network, then try again."
      );
    }
    throw e;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function asObject(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== "object" || Array.isArray(v)) return {};
  return v as Record<string, unknown>;
}

function trimText(v: unknown, max = 360): string | undefined {
  if (typeof v !== "string") return undefined;
  const s = v.trim();
  if (!s) return undefined;
  return s.length > max ? `${s.slice(0, max - 1)}\u2026` : s;
}

function sanitizeNarrativePercentages(v: string): string {
  return v
    .replace(/\b\d{1,3}\s*%/g, "high")
    .replace(/\b\d{1,3}\s*\/\s*100\b/g, "high")
    .replace(/\b\d{1,3}\s*percent\b/gi, "high");
}

/**
 * ElevenLabs tool responses travel over the realtime channel. Keep this payload compact to
 * avoid oversized messages that can destabilize long voice sessions.
 */
function compactResearchToolResult(raw: string): string {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return raw;
  }
  const o = asObject(parsed);
  const out: Record<string, unknown> = {};

  if ("research_complete" in o) out.research_complete = o.research_complete;

  const reportNumbers = asObject(o.report_numbers);
  if (Object.keys(reportNumbers).length > 0) {
    out.report_numbers = reportNumbers;
    const canonical = [
      "currency_code",
      "grade",
      "grade_score",
      "estimated_tuition",
      "tuition_web_estimate",
      "tuition_if_invested",
      "tuition_opportunity_gap",
      "avg_salary_for_degree",
      "avg_salary_for_role",
      "median_salary_for_role",
      "salary_range_low",
      "salary_range_high",
      "degree_roi_rank",
      "job_market_trend",
      "ai_replacement_risk_0_100",
      "near_term_ai_risk_0_100",
      "career_market_stress_0_100",
      "financial_roi_stress_0_100",
      "overall_cooked_0_100",
    ] as const;
    for (const k of canonical) {
      if (k in reportNumbers) out[k] = reportNumbers[k];
    }
  } else {
    const legacy = [
      "grade",
      "grade_score",
      "currency_code",
      "estimated_tuition",
      "tuition_web_estimate",
      "tuition_if_invested",
      "tuition_opportunity_gap",
      "avg_salary_for_degree",
      "avg_salary_for_role",
      "median_salary_for_role",
      "salary_range_low",
      "salary_range_high",
      "degree_roi_rank",
      "job_market_trend",
      "ai_replacement_risk_0_100",
      "near_term_ai_risk_0_100",
      "career_market_stress_0_100",
      "financial_roi_stress_0_100",
      "overall_cooked_0_100",
    ] as const;
    for (const k of legacy) {
      if (k in o) out[k] = o[k];
    }
  }

  const tips = Array.isArray(o.safeguard_tips)
    ? o.safeguard_tips
        .map((x) => trimText(x, 280))
        .filter((x): x is string => Boolean(x))
        .map((x) => sanitizeNarrativePercentages(x))
        .slice(0, 6)
    : [];
  if (tips.length > 0) out.safeguard_tips = tips;

  const sources = Array.isArray(o.sources)
    ? o.sources
        .map((s) => {
          const row = asObject(s);
          const title = trimText(row.title, 160);
          const url = trimText(row.url, 220);
          const topic = trimText(row.topic, 200);
          return { title, url, topic };
        })
        .slice(0, 8)
    : [];
  if (sources.length > 0) out.sources = sources;

  const namedSources = Array.isArray(o.named_sources)
    ? o.named_sources
        .map((x) => trimText(x, 80))
        .filter((x): x is string => Boolean(x))
        .slice(0, 10)
    : [];
  if (namedSources.length > 0) out.named_sources = namedSources;

  const searchQueries = Array.isArray(o.search_queries)
    ? o.search_queries
        .map((x) => trimText(x, 120))
        .filter((x): x is string => Boolean(x))
        .slice(0, 10)
    : [];
  if (searchQueries.length > 0) out.search_queries = searchQueries;

  const searchHitCounts = Array.isArray(o.search_hit_counts)
    ? o.search_hit_counts.slice(0, 10)
    : [];
  if (searchHitCounts.length > 0) out.search_hit_counts = searchHitCounts;

  const aiRiskReasoningRaw = trimText(o.ai_risk_reasoning, 900);
  const aiRiskReasoning = aiRiskReasoningRaw
    ? sanitizeNarrativePercentages(aiRiskReasoningRaw)
    : undefined;
  if (aiRiskReasoning) out.ai_risk_reasoning = aiRiskReasoning;

  const honestTakeRaw = trimText(o.honest_take, 700);
  const honestTake = honestTakeRaw
    ? sanitizeNarrativePercentages(honestTakeRaw)
    : undefined;
  if (honestTake) out.honest_take = honestTake;

  const methodologyNote = trimText(o.methodology_note, 280);
  if (methodologyNote) out.methodology_note = methodologyNote;

  const agentNote = trimText(o.agent_note, 1200);
  if (agentNote) out.agent_note = agentNote;

  try {
    return JSON.stringify(out);
  } catch {
    return raw;
  }
}

/**
 * Normalize inline profile for `research_degree` (not stored on session).
 * Accepts: JSON string, `{ profile }`, `{ profiles: [ {...} ] }`, top-level array `[ {...} ]`, camelCase.
 */
function normalizeVoiceProfilePayload(parameters: unknown): Record<string, unknown> {
  let raw: unknown = parameters;
  if (typeof raw === "string") {
    try {
      raw = JSON.parse(raw) as unknown;
    } catch {
      return {};
    }
  }
  let o = asObject(raw);
  if (Array.isArray(raw) && raw.length > 0) {
    o = asObject(raw[0]);
  }
  const profiles = o.profiles;
  if (Array.isArray(profiles) && profiles.length > 0) {
    o = asObject(profiles[0]);
  }
  const inner = o.profile;
  if (inner && typeof inner === "object" && !Array.isArray(inner)) {
    o = { ...o, ...asObject(inner) };
    delete o.profile;
  }
  const camelToSnake: Record<string, string> = {
    major: "major",
    university: "university",
    cgpa: "cgpa",
    yearOfStudy: "year_of_study",
    skills: "skills",
    courses: "courses",
    experience: "experience",
    languagesKnown: "languages_known",
    targetCompanies: "target_companies",
    sessionId: "session_id",
    countryOrRegion: "country_or_region",
  };
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(o)) {
    const nk = camelToSnake[k] ?? k;
    if (nk === "session_id" || nk === "sessionId") continue;
    out[nk] = v;
  }
  const digits = (x: unknown) => (typeof x === "string" && /^\d+$/.test(x) ? parseInt(x, 10) : x);
  if ("cgpa" in out) {
  const v = parseFloat(String(out.cgpa));
  out.cgpa = Number.isFinite(v) ? v : null;
}
  if ("country_or_region" in out && typeof out.country_or_region === "string") {
  out.country_or_region = out.country_or_region.trim();
  }
  if ("target_companies" in out) {
    if (typeof out.target_companies === "string") {
      out.target_companies = out.target_companies
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
  }
  if ("skills" in out) {
    if (typeof out.skills === "string") {
      out.skills = out.skills
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
  }
  if ("languages_known" in out) {
    if (typeof out.languages_known === "string") {
      out.languages_known = out.languages_known
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
  }
  if ("courses" in out) {
    if (typeof out.courses === "string") {
      out.courses = out.courses
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
  }
  if ("year_of_study" in out) {
    const v = String(out.year_of_study ?? "").toLowerCase().trim();
    if (v === "1" || v.includes("first")) out.year_of_study = 1;
    else if (v === "2" || v.includes("second")) out.year_of_study = 2;
    else if (v === "3" || v.includes("third")) out.year_of_study = 3;
    else if (v === "4" || v.includes("fourth")) out.year_of_study = 4;
    else out.year_of_study = digits(out.year_of_study);
  }
  return out;
}

export default function DonaldConversation({
  sessionId,
  onComplete,
  onSdkActivity,
  preloadedCv,
  autoStart = false,
  onCvAnalysis,
}: Props) {
  const [started, setStarted] = useState(false);
  const [statusText, setStatusText] = useState("Donald is ready. are you?");
  const [phase, setPhase] = useState<"idle" | "connecting" | "talking" | "done">("idle");
  const [cvPhase, setCvPhase] = useState<"idle" | "uploading" | "sent">(preloadedCv ? "sent" : "idle");
  const cvInputRef = useRef<HTMLInputElement>(null);
  const cvPushedRef = useRef(false);
  const debugLogged = useRef(0);
  const metaLogged = useRef(false);
  const autoStartAttemptedRef = useRef(false);

  const pushRef = useRef(onSdkActivity);
  pushRef.current = onSdkActivity;

  const emit = useCallback((row: Omit<VoiceActivityRow, "id" | "ts" | "source"> & { id?: string; ts?: number }) => {
    voiceDevLog("activity_emit", `${row.event}: ${row.title}`, {
      detail: row.detail,
      data: row.data ?? null,
    });
    pushRef.current?.({
      id: row.id ?? rid(),
      ts: row.ts ?? Date.now(),
      source: "live",
      event: row.event,
      title: row.title,
      detail: row.detail,
      data: row.data,
    });
  }, []);

  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const emitRef = useRef(emit);
  emitRef.current = emit;

  /** Latest conversation API -- set after `useConversation` so client tools can nudge the agent. */
  const conversationNudgeRef = useRef<{
    sendUserMessage: (t: string) => void;
    sendContextualUpdate: (t: string) => void;
  } | null>(null);

  /**
   * Push pre-loaded CV context into the agent after the connection is established.
   */
  const pushPreloadedCv = useCallback(() => {
    if (!preloadedCv || cvPushedRef.current) return;
    cvPushedRef.current = true;
    const compact = compactCvForVoice(preloadedCv);
    voiceDevLog("cv", "pushing pre-loaded CV to agent", { compact });

    const conv = conversationNudgeRef.current;
    if (!conv) return;
    try {
      conv.sendContextualUpdate(
        `The user uploaded their CV before joining. Here is the structured analysis from Claude:\n${compact}\n\n` +
        `INSTRUCTIONS — READ CAREFULLY:\n` +
        `1. You already have their full profile from the CV — name, current role, company, education, skills, and experience. Do NOT ask them what they do, where they work, what they studied, or any basic info that's already in the profile above.\n` +
        `2. Greet them by name and reference their role/company naturally.\n` +
        `3. You MUST still call research_degree using the profile data extracted from the CV. Build the profile object from what you have: degree, university, graduation_year, current_job, current_company, years_experience, country_or_region. Run the research — the user still needs their roast numbers.\n` +
        `4. If you need any info that's NOT in the CV (e.g. salary, tuition paid, specific graduation year if unclear), ask only those specific missing pieces. Do not re-ask anything already provided.\n` +
        `5. Walk them through CV coaching (score, fixes, donald_take) either before or after the research — your call on timing. Keep it punchy, roasty, useful.\n` +
        `6. Do NOT ask them to upload a CV again. Do NOT read data back like a report — turn each point into a conversational coaching beat.`,
      );
      emit({
        event: "cv_ready",
        title: "CV pre-loaded",
        detail: `Score: ${preloadedCv.overall_score_0_100}/100 -- Donald has your CV analysis ready.`,
        data: { cv_analysis: preloadedCv },
      });
    } catch (err) {
      voiceDevLog("cv", "pre-loaded CV push failed", err);
    }
  }, [preloadedCv, emit]);

  /**
   * ElevenLabs *client* tools (browser -> your API). Voice flow does not persist profile on the session;
   * the agent passes an inline `profile` into `research_internship` for Firecrawl + Claude.
   */
  const voiceClientTools = useMemo(
    () => ({
      research_internship: async (parameters?: Record<string, unknown>) => {
        const sid = sessionIdRef.current;
        const profile = normalizeVoiceProfilePayload(parameters);
        const n = Object.keys(profile).length;
        voiceDevLog("client_tool", "research_internship invoked invoked", {
          session_id: sid,
          raw_parameters: parameters ?? null,
          normalized_profile: profile,
        });
        emitRef.current({
          event: "client_tool",
          title: VOICE_RESEARCH_CLIENT_START_TITLE,
          detail:
            n === 0
              ? "Donald still needs your school, degree, grad year, and job -- answer him first, then he can run this again."
              : "Pulling public salary, tuition, and job-market info. Usually under a minute -- stay on this tab.",
        });
        try {
          const rawOut = await postWebhook(
            "/api/webhooks/research_internship",
            { session_id: sid, profile },
            { timeoutMs: RESEARCH_WEBHOOK_TIMEOUT_MS }
          );
          const out = compactResearchToolResult(rawOut);
          voiceDevLog("client_tool", "research_degree return", {
            returnPreview: typeof out === "string" ? voiceDevJson(out, 12000) : out,
          });
          emitRef.current({
            event: "client_tool",
            title: VOICE_RESEARCH_CLIENT_DONE_TITLE,
            detail: "Donald's got the facts -- he'll keep the roast going. Peek at the feed if you're curious what we checked.",
          });
          queueMicrotask(() => {
            const conv = conversationNudgeRef.current;
            if (!conv) return;
            try {
              conv.sendContextualUpdate(
                "research_degree finished: research_complete is true in the tool result you received. Continue speaking immediately -- start the roast. Do not ask the user to confirm research loaded."
              );
              conv.sendUserMessage(APP_RESEARCH_DONE_NUDGE);
            } catch (err) {
              voiceDevLog("nudge", "post-research agent nudge failed", err);
            }
          });
          return out;
        } catch (e) {
          const msg = e instanceof Error ? e.message : "request failed";
          voiceDevLog("client_tool", "research_degree error", { error: msg });
          emitRef.current({
            event: "client_tool_error",
            title: VOICE_RESEARCH_CLIENT_ERROR_TITLE,
            detail: userFacingErrorMessage(msg),
          });
          return JSON.stringify({
            error: msg,
            research_complete: false,
            agent_note:
              "Research failed -- do not roast. Briefly apologize and ask them to check connection or fill missing profile fields, then retry research_degree.",
          });
        }
      },
      save_roast_quote: async (parameters?: Record<string, unknown>) => {
        const sid = sessionIdRef.current;
        const p = parameters ?? {};
        const quote = typeof p.quote === "string" ? p.quote : "";
        voiceDevLog("client_tool", "save_roast_quote invoked", {
          session_id: sid,
          raw_parameters: parameters ?? null,
          quoteLength: quote.length,
        });
        emitRef.current({
          event: "client_tool",
          title: "Saving your best line",
          detail: quote ? `"${quote.slice(0, 120)}${quote.length > 120 ? "\u2026" : ""}"` : "Nothing to save yet.",
        });
        try {
          const out = await postWebhook("/api/webhooks/save_roast_quote", { session_id: sid, quote });
          voiceDevLog("client_tool", "save_roast_quote return", {
            returnPreview: typeof out === "string" ? voiceDevJson(out, 2000) : out,
          });
          emitRef.current({
            event: "client_tool",
            title: "Line saved",
            detail: "It'll show up on your report card when you open it.",
          });
          return out;
        } catch (e) {
          const msg = e instanceof Error ? e.message : "request failed";
          voiceDevLog("client_tool", "save_roast_quote error", { error: msg });
          emitRef.current({
            event: "client_tool_error",
            title: "Couldn't save that line",
            detail: userFacingErrorMessage(msg),
          });
          return JSON.stringify({ error: msg, saved: false });
        }
      },
    }),
    []
  );

  const conversation = useConversation({
    clientTools: voiceClientTools,
    onConnect: (props) => {
      voiceDevLog("sdk", "onConnect", props);
      setPhase("talking");
      setStatusText("connected. Donald is listening...");
      emit({ event: "connect", title: "You're live with Donald", detail: "He can hear you -- go ahead and talk." });

      if (preloadedCv && !cvPushedRef.current) {
        queueMicrotask(() => pushPreloadedCv());
      }
    },
    onConversationMetadata: (meta) => {
      voiceDevLog("sdk", "onConversationMetadata", meta);
      if (metaLogged.current) return;
      metaLogged.current = true;
      let detail = "";
      try {
        detail = JSON.stringify(meta).slice(0, 320);
      } catch {
        detail = "[metadata]";
      }
      emit({ event: "conversation_meta", title: "Session ready", detail: "" });
    },
    onDisconnect: (details) => {
      voiceDevLog("sdk", "onDisconnect", details);
      emit({
        event: "disconnect",
        title: "Call ended",
        detail:
          details.reason === "error"
            ? userFacingErrorMessage(details.message || "")
            : details.reason === "user"
              ? "You ended the call."
              : "The call ended.",
      });
      setPhase("done");
      if (details.reason === "error") {
        setStatusText("Call dropped. Try again in a moment.");
        return;
      }
      setStatusText("the verdict has been delivered.");
      setTimeout(onComplete, 2500);
    },
    onError: (message, context) => {
      voiceDevLog("sdk", "onError", { message, context });
      console.error(message, context);
      emit({
        event: "error",
        title: "Something went wrong",
        detail: typeof message === "string" ? userFacingErrorMessage(message) : "Please try again.",
      });
      setStatusText("connection lost. even Donald has off days fr.");
      setPhase("done");
    },
    onStatusChange: ({ status }) => {
      voiceDevLog("sdk", "onStatusChange", { status });
      emit({ event: "status", title: `Link status: ${status}` });
    },
    onModeChange: ({ mode }) => {
      voiceDevLog("sdk", "onModeChange", { mode });
      emit({
        event: "mode",
        title: mode === "speaking" ? "Donald is speaking" : "Listening",
        detail: mode,
      });
    },
    onMessage: (props) => {
      voiceDevLog("sdk", "onMessage", {
        role: props.role,
        message: props.message,
        source: props.source,
      });
      const text = (props.message || "").trim();
      if (!text) return;
      if (props.role === "user" && (text.startsWith(APP_RESEARCH_DONE_SENTINEL) || text.startsWith(APP_CV_READY_SENTINEL))) {
        voiceDevLog("sdk", "onMessage skipped app nudge (not shown in activity feed)");
        return;
      }
      const title = props.role === "user" ? "You said" : "Donald said";
      emit({
        event: "transcript",
        title,
        detail: text.length > 420 ? `${text.slice(0, 419)}\u2026` : text,
      });
    },
    onAgentToolRequest: (p) => {
      voiceDevLog("sdk", "onAgentToolRequest (server/webhook tool path)", p);
      const tn = p.tool_name || "";
      const isOurs = isVoiceClientToolName(tn);
      emit({
        event: "agent_tool_request",
        title: toolLine(tn),
        detail: isOurs
          ? `ElevenLabs triggered "${tn}" on the server (${p.tool_type || "type ?"}). This app only runs that tool in the **browser** (Client tool). In ElevenLabs > Agent > Tools, set ${tn} to **Client** and import \`prompts/elevenlabs-client-tools.json\`.`
          : "One moment\u2026",
      });
    },
    onAgentToolResponse: (p) => {
      voiceDevLog("sdk", "onAgentToolResponse", p);
      emit({
        event: "agent_tool_response",
        title: "Done",
        detail: p.is_error ? "That part didn't work -- you can still talk to Donald." : "Back to the conversation.",
      });
    },
    onAgentChatResponsePart: (part) => {
      voiceDevLog("sdk", "onAgentChatResponsePart", part);
      if (part.type === "start") {
        emit({ event: "agent_stream", title: "Donald is composing\u2026", detail: "Streaming response" });
      }
    },
    onUnhandledClientToolCall: (params) => {
      voiceDevLog("sdk", "onUnhandledClientToolCall", params);
      const tn = params.tool_name || "";
      emit({
        event: "client_tool_unhandled",
        title: "Tool name mismatch",
        detail: tn
          ? `The agent called "${tn}" but this page only handles: research_degree, save_roast_quote. Fix the tool name in ElevenLabs to match exactly (snake_case).`
          : "Donald tried a client tool this build doesn't handle. Check ElevenLabs tool names match research_degree and save_roast_quote.",
      });
    },
    onInterruption: VOICE_DEV_LOG
      ? (ev) => {
          voiceDevLog("sdk", "onInterruption", ev);
        }
      : undefined,
    onDebug:
      VOICE_DEV_LOG || VOICE_SDK_DEBUG
        ? (payload) => {
            if (VOICE_DEV_LOG) {
              voiceDevLog("sdk_raw", "onDebug", typeof payload === "object" ? voiceDevJson(payload, 12000) : payload);
            }
            if (VOICE_SDK_DEBUG) {
              if (debugLogged.current >= 80) return;
              debugLogged.current += 1;
              let detail = "";
              try {
                detail = typeof payload === "object" ? JSON.stringify(payload).slice(0, 240) : String(payload).slice(0, 240);
              } catch {
                detail = "[unserializable]";
              }
              emit({ event: "sdk_debug", title: "SDK debug", detail });
            }
          }
        : undefined,
  });

  conversationNudgeRef.current = {
    sendUserMessage: conversation.sendUserMessage.bind(conversation),
    sendContextualUpdate: conversation.sendContextualUpdate.bind(conversation),
  };

  const isSpeaking = conversation.isSpeaking;

  useEffect(() => {
    if (phase === "talking") {
      setStatusText(isSpeaking ? "Donald's talking..." : "your turn. speak now.");
    }
  }, [isSpeaking, phase]);

  useEffect(() => {
    if (preloadedCv) onCvAnalysis?.(preloadedCv);
  }, [preloadedCv, onCvAnalysis]);

  const handleCvUpload = useCallback(
    async (file: File) => {
      setCvPhase("uploading");
      emit({
        event: "cv_upload",
        title: "Uploading your CV",
        detail: `Reading ${file.name}\u2026`,
      });
      try {
        const { analysis } = await uploadCV(file, sessionId);
        onCvAnalysis?.(analysis);
        const compact = compactCvForVoice(analysis);
        voiceDevLog("cv", "analysis ready, pushing to agent", { compact });

        const conv = conversationNudgeRef.current;
        if (conv) {
          conv.sendContextualUpdate(
            `The user just uploaded their CV mid-call. Here is the structured analysis from Claude:\n${compact}\n\n` +
            `INSTRUCTIONS — READ CAREFULLY:\n` +
            `1. You now have their full profile — name, current role, company, education, skills, experience. Do NOT ask them what they do, where they work, or any basic info already in the profile above.\n` +
            `2. You MUST still call research_degree using the profile data from the CV. Build the profile object from what you have: degree, university, graduation_year, current_job, current_company, years_experience, country_or_region. The user still needs their roast numbers — run the research.\n` +
            `3. If you need any info NOT in the CV (e.g. salary, tuition paid, specific graduation year if ambiguous), ask only those specific missing pieces. Do not re-ask anything already provided.\n` +
            `4. Walk the user through the CV coaching: score, verdict, critical fixes, donald_take. Keep it punchy, roasty, useful. Do NOT read the data like a report — turn each point into a conversational coaching beat.\n` +
            `5. Do NOT ask them to upload a CV again.`,
          );
          conv.sendUserMessage(
            `${APP_CV_READY_SENTINEL}I just uploaded my CV. Walk me through it.`,
          );
        }

        emit({
          event: "cv_ready",
          title: "CV analysis ready",
          detail: `Score: ${analysis.overall_score_0_100}/100 -- Donald has the results.`,
          data: { cv_analysis: analysis },
        });
        setCvPhase("sent");
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Upload failed";
        emit({
          event: "cv_error",
          title: "CV upload failed",
          detail: msg,
        });
        setCvPhase("idle");
      }
    },
    [sessionId, emit],
  );

  const start = useCallback(async () => {
    setPhase("connecting"); setStatusText("connecting you to Donald...");
    const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;
    if (!agentId) {
      setStatusText("missing NEXT_PUBLIC_ELEVENLABS_AGENT_ID in .env.local");
      setPhase("idle");
      return;
    }
    const dynamicVariables: Record<string, string | number | boolean> = {
      session_id: sessionId,
      sessionId,
      error_event: "none",
      errorEvent: "none",
    };

    if (preloadedCv) {
      dynamicVariables.cv_uploaded = true;
      dynamicVariables.cv_score = preloadedCv.overall_score_0_100;
      dynamicVariables.cv_verdict = preloadedCv.overall_summary;
      if (preloadedCv.file_name) dynamicVariables.cv_file_name = preloadedCv.file_name;
      if (preloadedCv.candidate_name) dynamicVariables.cv_name = preloadedCv.candidate_name;
      if (preloadedCv.current_role) dynamicVariables.cv_role = preloadedCv.current_role;
      if (preloadedCv.current_company) dynamicVariables.cv_company = preloadedCv.current_company;
      if (preloadedCv.education?.length) {
        dynamicVariables.cv_degree = preloadedCv.education[0].degree;
        dynamicVariables.cv_university = preloadedCv.education[0].institution;
      }
    }

    voiceDevLog("session", "startSession requested", {
      agentId,
      useToken: USE_CONVAI_TOKEN,
      branchId: BRANCH_ID || null,
      dynamicVariables,
    });
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });

      if (USE_CONVAI_TOKEN) {
        const url = new URL(`${API_URL}/api/convai/conversation-token`);
        url.searchParams.set("agent_id", agentId);
        if (BRANCH_ID) url.searchParams.set("branch_id", BRANCH_ID);
        voiceDevLog("session", "Fetching conversation token", { url: url.toString() });
        const res = await fetch(url.toString());
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(errText || `token ${res.status}`);
        }
        const { token } = (await res.json()) as { token: string };
        voiceDevLog("session", "startSession (token + webrtc)", {
          tokenPreview: `${token.slice(0, 12)}\u2026(${token.length} chars)`,
          dynamicVariables,
        });
        await conversation.startSession({
          conversationToken: token,
          connectionType: "webrtc",
          dynamicVariables,
        });
      } else {
        voiceDevLog("session", "startSession (public agentId + webrtc)", { agentId, dynamicVariables });
        await conversation.startSession({
          agentId,
          connectionType: "webrtc",
          dynamicVariables,
        });
      }
      emit({
        event: "webrtc_ready",
        title: "You're connected",
        detail: "Mic is on -- say hi to Donald.",
      });
      setStarted(true);
    } catch (e) {
      voiceDevLog("session", "startSession failed", {
        error: e instanceof Error ? e.message : String(e),
        name: e instanceof Error ? e.name : undefined,
      });
      console.error(e);
      setStatusText(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Mic access is required so Donald can hear you."
          : "Couldn't connect. Check your internet and try again."
      );
      setPhase("idle");
    }
  }, [conversation, sessionId, emit, preloadedCv]);

  useEffect(() => {
    if (!autoStart || started || phase !== "idle" || autoStartAttemptedRef.current) return;
    autoStartAttemptedRef.current = true;
    void start();
  }, [autoStart, started, phase, start]);

  const end = useCallback(async () => {
    voiceDevLog("session", "endSession (user clicked End)");
    await conversation.endSession();
  }, [conversation]);

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-sm mx-auto">
      {/* Avatar orb */}
      <motion.div
        animate={isSpeaking ? { scale: [1, 1.06, 1] } : { scale: 1 }}
        transition={isSpeaking ? { duration: 1.5, repeat: Infinity, ease: "easeInOut" as const } : { duration: 0.4 }}
        className={`relative w-32 h-32 rounded-full flex items-center justify-center transition-shadow duration-700 ${
          isSpeaking ? "bg-[var(--gold)]/10 border-2 border-[var(--gold)] shadow-[0_0_50px_rgba(245,166,35,0.15)]"
          : phase === "talking" ? "bg-[var(--card)] border-2 border-[var(--gold)]/30"
          : "bg-[var(--card)] border border-white/10"
        }`}
      >
        <DonaldLogo className={`scale-[1.8] transition-colors duration-500 ${isSpeaking ? "text-[var(--gold)]" : "text-[var(--fg)]"}`} />
      </motion.div>

      {/* Audio bars */}
      <div className="flex items-end gap-[3px] h-6">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="w-[3px] rounded-full bg-[var(--gold)] transition-all duration-200"
            style={{
              height: isSpeaking ? `${10 + ((i * 7 + 3) % 14)}px` : "3px",
              opacity: isSpeaking ? 0.5 + (i % 3) * 0.2 : 0.15,
              animationDelay: `${i * 80}ms`,
            }} />
        ))}
      </div>

      {/* Status */}
      <AnimatePresence mode="wait">
        <motion.p key={statusText} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.25 }}
          className="text-[var(--subtle)] text-sm text-center font-light">
          {statusText}
        </motion.p>
      </AnimatePresence>

      {/* Controls */}
      {!started ? (
        <motion.button onClick={start} disabled={phase === "connecting"}
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          className="flex items-center gap-2.5 px-8 py-3.5 bg-[var(--gold)] text-black font-semibold text-sm rounded-xl hover:bg-[var(--gold-dim)] transition-colors glow-gold disabled:opacity-50">
          {phase === "connecting"
            ? <span className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
            : <MicIcon size={18} />}
          {phase === "connecting" ? "Connecting..." : "Talk to Donald"}
        </motion.button>
      ) : phase !== "done" ? (
        <div className="flex flex-col items-center gap-2">
          <p className="text-[10px] text-[var(--subtle)]/80 text-center">
            End the call when you are ready to open your report.
          </p>
          <button onClick={end} className="px-5 py-2 bg-[var(--card)] border border-white/10 rounded-lg text-xs text-[var(--subtle)] hover:text-[var(--fg)] hover:border-white/20 transition-all">
            End Conversation
          </button>
        </div>
      ) : (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-[var(--gold)] text-xs font-display italic">
          Redirecting to your vibe sheet...
        </motion.p>
      )}

      {phase === "idle" && (
        <p className="text-[var(--subtle)]/50 text-xs text-center max-w-xs">
          This is a live voice conversation. Donald will ask for your degree and work details, then deliver his verdict.
        </p>
      )}

      {/* CV upload during call (always available while talking) */}
      {phase === "talking" && (
        <div className="w-full max-w-xs">
          <input
            ref={cvInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleCvUpload(f);
            }}
            className="hidden"
          />

          {cvPhase === "uploading" ? (
            <div className="flex items-center justify-center gap-2 py-2 text-xs text-[var(--subtle)]">
              <span className="w-3 h-3 border-2 border-transparent border-t-[var(--gold)] rounded-full animate-spin" />
              Analyzing your CV...
            </div>
          ) : (
            <div className="text-center">
              {cvPhase === "sent" ? (
                <p className="text-[var(--gold)] text-xs mb-1.5">
                  CV loaded. Upload another anytime.
                </p>
              ) : null}
              <button
                onClick={() => {
                  if (cvInputRef.current) cvInputRef.current.value = "";
                  cvInputRef.current?.click();
                }}
                className="w-full py-2 px-4 rounded-lg border border-dashed border-white/10 bg-[var(--card)] hover:border-[var(--gold-dim)] text-xs text-[var(--subtle)] hover:text-[var(--fg)] transition-all text-center"
              >
                Upload CV (PDF/DOCX/TXT)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
