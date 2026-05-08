"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getDegreeTier } from "@/lib/degreeTier";

interface ResearchSourceRow {
  title: string;
  url: string;
  topic: string;
}

interface JobTaskExposureRow {
  task: string;
  time_pct: number;
  automation_score_0_100: number;
  reasoning?: string;
  timeline_horizon?: string;
}

interface ReportCardData {
  session_id: string; grade: string; grade_score: number;
  profile: {
    name: string;
    degree: string;
    university: string;
    graduation_year: number;
    current_job: string;
    years_experience?: number | null;
    country_or_region?: string | null;
    currency_code?: string | null;
  };
  research: {
    currency_code?: string | null;
    avg_salary_for_degree: number | null;
    avg_salary_for_role?: number | null;
    median_salary_for_role?: number | null;
    estimated_tuition: number | null;
    tuition_web_estimate?: number | null;
    tuition_if_invested: number | null;
    tuition_opportunity_gap?: number | null;
    degree_roi_rank: string | null;
    job_market_trend: string | null;
    ai_replacement_risk_0_100?: number | null;
    ai_risk_reasoning?: string;
    near_term_ai_risk_0_100?: number | null;
    career_market_stress_0_100?: number | null;
    financial_roi_stress_0_100?: number | null;
    overall_cooked_0_100?: number | null;
    job_task_exposure?: JobTaskExposureRow[];
    safeguard_tips?: string[];
    honest_take?: string;
    methodology_note?: string;
    named_sources?: string[];
    sources?: ResearchSourceRow[];
  };
  roast_quote: string;
}

function fmtMoney(n: number | null | undefined, currency = "USD") {
  if (n == null) return "\u2014";
  const code = /^[A-Z]{3}$/i.test(currency) ? currency.toUpperCase() : "USD";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      maximumFractionDigits: 0,
    }).format(Number(n));
  } catch {
    return `${Number(n).toLocaleString()} ${code}`;
  }
}

function horizonShort(h: string | undefined): string {
  const m: Record<string, string> = {
    now: "Now",
    "1_2_years": "1–2y",
    "3_5_years": "3–5y",
    longer: "Longer",
  };
  if (!h) return "—";
  return m[h] ?? h;
}

function RiskMeter({ label, value }: { label: string; value: number }) {
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between text-[10px] font-semibold tracking-wider uppercase text-[var(--subtle)] mb-1.5">
        <span>{label}</span>
        <span className="text-[var(--fg)]">{value}/100</span>
      </div>
      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="h-full rounded-full bg-gradient-to-r from-[var(--gold)] to-[var(--red)]"
        />
      </div>
    </div>
  );
}

export default function ReportCard({ data }: { data: ReportCardData }) {
  const [show, setShow] = useState(false);
  const tier = getDegreeTier(data.grade);
  useEffect(() => { setTimeout(() => setShow(true), 600); }, []);

  const cc =
    data.research.currency_code ||
    data.profile.currency_code ||
    "USD";

  const oppRaw =
    data.research.tuition_opportunity_gap ??
    (data.research.estimated_tuition != null && data.research.tuition_if_invested != null
      ? data.research.tuition_if_invested - data.research.estimated_tuition
      : null);

  const stats = [
    { label: "Tuition Paid", val: fmtMoney(data.research.estimated_tuition, cc) },
    ...(data.research.tuition_web_estimate != null && data.research.tuition_web_estimate > 0
      ? [
          {
            label: "Web tuition estimate",
            val: fmtMoney(data.research.tuition_web_estimate, cc),
          },
        ]
      : []),
    { label: "Degree Avg Salary", val: fmtMoney(data.research.avg_salary_for_degree, cc) },
    ...(data.research.avg_salary_for_role != null
      ? [{ label: "Role Avg Salary", val: fmtMoney(data.research.avg_salary_for_role, cc) }]
      : []),
    ...(data.research.median_salary_for_role != null
      ? [{ label: "Role Median Salary", val: fmtMoney(data.research.median_salary_for_role, cc) }]
      : []),
    { label: "If You\u2019d Invested", val: fmtMoney(data.research.tuition_if_invested, cc), red: true },
    { label: "Job Market", val: data.research.job_market_trend ? data.research.job_market_trend.charAt(0).toUpperCase() + data.research.job_market_trend.slice(1) : "\u2014" },
  ];

  const aiRisk = data.research.ai_replacement_risk_0_100;
  const nearTermAi = data.research.near_term_ai_risk_0_100;
  const careerStress = data.research.career_market_stress_0_100;
  const financialStress = data.research.financial_roi_stress_0_100;
  const cooked = data.research.overall_cooked_0_100;
  const taskRows = (data.research.job_task_exposure ?? []).filter((t) => t.task?.trim());
  const tips = (data.research.safeguard_tips ?? []).slice(0, 3);
  const namedSources = (data.research.named_sources ?? []).filter(Boolean).slice(0, 5);
  const sourceRows = (data.research.sources ?? []).filter((s) => s.title || s.url);
  const methodology = (data.research.methodology_note ?? "").trim();
  const hasAttribution =
    Boolean(methodology) || namedSources.length > 0 || sourceRows.length > 0;

  return (
    <div className="w-full max-w-md mx-auto space-y-5">
    <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
      className="bg-[var(--card)] rounded-2xl border border-white/5 overflow-hidden">

      {/* Header */}
      <div className="px-7 pt-7 pb-5 text-center border-b border-white/5">
        <p className="text-[var(--subtle)] text-[10px] font-semibold tracking-[0.25em] uppercase mb-5">Donald&apos;s AI job-risk label</p>

        {/* Label from API grade (A–F); long phrases use a pill instead of a circle */}
        <motion.div initial={{ scale: 0, rotate: -180 }} animate={show ? { scale: 1, rotate: 0 } : {}} transition={{ type: "spring", stiffness: 180, damping: 14, delay: 0.2 }}
          className={`mx-auto mb-4 flex flex-col items-center justify-center border-[3px] px-4 py-4 ${
            tier.badge.length > 10 ? "min-h-[5.5rem] w-full max-w-[15rem] rounded-2xl" : "h-28 w-28 sm:h-32 sm:w-32 rounded-full"
          }`}
          style={{ background: `${tier.color}10`, borderColor: `${tier.color}80` }}>
          <motion.span initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 0.8 }}
            className={`font-display font-bold text-center leading-tight ${tier.badge.length > 10 ? "text-base sm:text-lg" : "text-2xl sm:text-3xl leading-none px-1"}`}
            style={{ color: tier.color }}>{tier.badge}</motion.span>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1 }}>
          <p className="text-xs font-semibold mb-3 px-2" style={{ color: tier.color }}>{tier.vibeLine}</p>
          <p className="text-lg font-semibold">{data.profile.name}</p>
          <p className="text-[var(--subtle)] text-sm font-light mt-0.5">{data.profile.degree} &mdash; {data.profile.university} ({data.profile.graduation_year})</p>
          <p className="text-[var(--subtle)]/50 text-xs mt-0.5">
            {data.profile.current_job}
            {data.profile.years_experience != null && data.profile.years_experience > 0 && (
              <span className="text-[var(--subtle)]/40"> · {data.profile.years_experience} yrs experience</span>
            )}
          </p>
          {(() => {
            const regionLine = [data.profile.country_or_region?.trim(), cc !== "USD" ? cc : null]
              .filter(Boolean)
              .join(" · ");
            return regionLine ? (
              <p className="text-[var(--subtle)]/35 text-[10px] mt-1 tracking-wide">{regionLine}</p>
            ) : null;
          })()}
        </motion.div>
      </div>

      {/* Stats */}
      <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1.2 }}
        className="grid grid-cols-2 divide-x divide-y divide-white/5">
        {stats.map((s) => (
          <div key={s.label} className="p-4 text-center">
            <p className="text-[var(--subtle)] text-[10px] font-semibold tracking-wider uppercase mb-1">{s.label}</p>
            <p className={`font-display text-base font-bold ${s.red ? "text-[var(--red)]" : ""}`}>{s.val}</p>
          </div>
        ))}
      </motion.div>

      {oppRaw != null && (
        <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1.15 }}
          className="px-7 py-3 border-t border-white/5 text-center">
          <p className="text-[var(--subtle)] text-[10px] font-semibold tracking-wider uppercase mb-1">Foregone gains (illustrative)</p>
          <p className="font-display text-lg font-bold text-[var(--red)]">{fmtMoney(oppRaw, cc)}</p>
          <p className="text-[var(--subtle)] text-[10px] mt-1 font-light">Tuition → S&P model; not financial advice</p>
        </motion.div>
      )}

      {(aiRisk != null ||
        nearTermAi != null ||
        careerStress != null ||
        financialStress != null ||
        cooked != null) && (
        <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1.25 }}
          className="px-7 py-5 border-t border-white/5 text-left">
          <p className="text-[10px] font-semibold tracking-wider uppercase text-[var(--subtle)] mb-3">Exposure + stress</p>
          {aiRisk != null && <RiskMeter label="AI exposure" value={aiRisk} />}
          {nearTermAi != null && <RiskMeter label="Near-term AI (0–2y horizon)" value={nearTermAi} />}
          {careerStress != null && <RiskMeter label="Career / market stress" value={careerStress} />}
          {financialStress != null && <RiskMeter label="Tuition ROI stress" value={financialStress} />}
          {cooked != null && <RiskMeter label="Overall cooked" value={cooked} />}
          {cooked != null && (careerStress != null || financialStress != null) && (
            <p className="text-[9px] text-[var(--subtle)]/70 mt-2 leading-relaxed">
              Cooked ≈ 55% AI + 25% market + 20% tuition stress (bars above).
            </p>
          )}
          {data.research.ai_risk_reasoning && (
            <p className="text-[var(--subtle)] text-[10px] mt-2.5 leading-relaxed italic line-clamp-5">
              {data.research.ai_risk_reasoning}
            </p>
          )}
          {!data.research.ai_risk_reasoning && (
            <p className="text-[var(--subtle)] text-[10px] mt-2 leading-relaxed">
              Higher = worse. Based on role, experience, and market signals.
            </p>
          )}
        </motion.div>
      )}

      {taskRows.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1.28 }}
          className="px-7 py-4 border-t border-white/5 text-left">
          <p className="text-[10px] font-semibold tracking-wider uppercase text-[var(--subtle)] mb-2.5">Task breakdown</p>
          <ul className="space-y-2.5">
            {taskRows.map((t, i) => (
              <li key={i} className="text-[10px] leading-snug border-l border-[var(--gold)]/35 pl-2.5">
                <span className="text-[var(--fg)]/95 font-medium">{t.task}</span>
                <span className="text-[var(--subtle)]/80">
                  {" "}
                  · {t.time_pct}% · exposure {t.automation_score_0_100}/100 · {horizonShort(t.timeline_horizon)}
                </span>
                {t.reasoning?.trim() ? (
                  <p className="text-[var(--subtle)]/75 font-light mt-0.5 line-clamp-3">{t.reasoning}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {tips.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1.35 }}
          className="px-7 py-4 border-t border-white/5">
          <p className="text-[10px] font-semibold tracking-wider uppercase text-[var(--subtle)] mb-2">Top moves</p>
          <ul className="space-y-2.5">
            {tips.map((tip, i) => (
              <li key={i} className="text-xs text-[var(--subtle)] font-light leading-relaxed pl-3 border-l border-[var(--gold)]/40">
                {tip}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* ROI Rank */}
      {data.research.degree_roi_rank && (
        <div className="px-7 py-2 border-t border-white/5 text-center">
          <p className="text-[var(--subtle)] text-[11px]">ROI rank <span className="text-[var(--fg)] font-medium">{data.research.degree_roi_rank}</span></p>
        </div>
      )}

      {/* Honest take — prefer LLM honest_take, fall back to roast_quote from voice agent */}
      {(data.research.honest_take || data.roast_quote) && (
        <motion.div initial={{ opacity: 0 }} animate={show ? { opacity: 1 } : {}} transition={{ delay: 1.5 }}
          className="px-7 py-4 border-t border-white/5">
          <p className="text-[10px] font-semibold tracking-wider uppercase text-[var(--subtle)] mb-2">Donald&apos;s honest take</p>
          <div className="pl-3 border-l-2 border-[var(--gold)]">
            <p className="font-display italic text-sm leading-relaxed line-clamp-5">&ldquo;{data.research.honest_take || data.roast_quote}&rdquo;</p>
            <p className="text-[var(--subtle)] text-[10px] mt-1">&mdash; Donald</p>
          </div>
        </motion.div>
      )}
    </motion.div>

    {hasAttribution && (
      <motion.aside
        initial={{ opacity: 0, y: 12 }}
        animate={show ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.45, delay: 1.45 }}
        className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-5 py-4"
        aria-label="Where this report’s information came from"
      >
        <p className="text-[10px] font-semibold tracking-wider uppercase text-[var(--subtle)] mb-1">
          Where this came from
        </p>
        <p className="text-[10px] text-[var(--subtle)]/75 leading-relaxed mb-3">
          Not part of the roast score — just the places we pulled salaries, tuition estimates, and market snippets from.
        </p>
        {methodology && (
          <p className="text-[10px] text-[var(--subtle)]/90 leading-snug mb-2.5">{methodology}</p>
        )}
        {namedSources.length > 0 && (
          <p className="text-[10px] text-[var(--subtle)] mb-2">
            <span className="font-semibold text-[var(--subtle)]/90">Named in snippets: </span>
            {namedSources.join(" · ")}
          </p>
        )}
        {sourceRows.length > 0 && (
          <ul className="space-y-1.5 pt-1 border-t border-white/5">
            {sourceRows.map((s, i) => (
              <li key={i} className="text-[11px] leading-snug">
                {s.url ? (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--gold)]/90 hover:underline font-medium break-words"
                  >
                    {s.title || s.url}
                  </a>
                ) : (
                  <span className="text-[var(--fg)]/80">{s.title}</span>
                )}
                {s.topic && (
                  <span className="block text-[9px] text-[var(--subtle)]/60 mt-0.5 line-clamp-2" title={s.topic}>
                    {s.topic}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </motion.aside>
    )}
    </div>
  );
}
