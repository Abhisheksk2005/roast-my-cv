"use client";

import { useState } from "react";
import type { CVAnalysisResult, CVSectionFeedback } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import AnnotatedCvText from "@/components/AnnotatedCvText";

const SEVERITY_CONFIG: Record<string, { dot: string; badge: string; border: string; bg: string; label: string }> = {
  critical: {
    dot: "bg-red-400",
    badge: "text-red-300 bg-red-400/10 border-red-400/20",
    border: "border-red-400/20",
    bg: "bg-red-400/[0.04]",
    label: "Critical",
  },
  important: {
    dot: "bg-amber-400",
    badge: "text-amber-300 bg-amber-400/10 border-amber-400/20",
    border: "border-amber-400/20",
    bg: "bg-amber-400/[0.04]",
    label: "Important",
  },
  suggestion: {
    dot: "bg-blue-400",
    badge: "text-blue-300 bg-blue-400/10 border-blue-400/20",
    border: "border-blue-400/20",
    bg: "bg-blue-400/[0.04]",
    label: "Suggestion",
  },
};

type Tab = "overview" | "fixes" | "profile";

function ScoreRing({ score }: { score: number }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = score >= 70 ? "#4ade80" : score >= 40 ? "#F5A623" : "#E63946";
  const grade =
    score >= 85 ? "S" : score >= 70 ? "A" : score >= 55 ? "B" : score >= 40 ? "C" : score >= 25 ? "D" : "F";

  return (
    <div className="relative w-28 h-28 flex-shrink-0">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
        <motion.circle
          cx="50" cy="50" r={radius} fill="none"
          stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold leading-none" style={{ color }}>{score}</span>
        <span className="text-[10px] text-[var(--subtle)] mt-0.5">grade {grade}</span>
      </div>
    </div>
  );
}

function ProfileCard({ analysis }: { analysis: CVAnalysisResult }) {
  const hasContact = analysis.candidate_email || analysis.candidate_phone || analysis.candidate_location;
  const hasEducation = analysis.education && analysis.education.length > 0;
  const hasExperience = analysis.experience_entries && analysis.experience_entries.length > 0;
  const hasSkills = analysis.skills && analysis.skills.length > 0;

  return (
    <div className="space-y-5">
      {/* Contact & role header */}
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-full bg-gradient-to-br from-[var(--gold)]/20 to-[var(--gold)]/5 border border-[var(--gold)]/20 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-semibold text-[var(--gold)]">
            {(analysis.candidate_name || "?")[0]?.toUpperCase()}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-[var(--fg)] truncate">
            {analysis.candidate_name || "Unknown Candidate"}
          </h4>
          {(analysis.current_role || analysis.current_company) && (
            <p className="text-xs text-[var(--fg)]/70 mt-0.5 truncate">
              {[analysis.current_role, analysis.current_company].filter(Boolean).join(" at ")}
              {analysis.experience_years ? ` · ${analysis.experience_years}y exp` : ""}
            </p>
          )}
          {hasContact && (
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
              {analysis.candidate_email && (
                <span className="text-[11px] text-[var(--subtle)] flex items-center gap-1">
                  <svg className="w-3 h-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
                  {analysis.candidate_email}
                </span>
              )}
              {analysis.candidate_phone && (
                <span className="text-[11px] text-[var(--subtle)] flex items-center gap-1">
                  <svg className="w-3 h-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                  {analysis.candidate_phone}
                </span>
              )}
              {analysis.candidate_location && (
                <span className="text-[11px] text-[var(--subtle)] flex items-center gap-1">
                  <svg className="w-3 h-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                  {analysis.candidate_location}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Experience */}
      {hasExperience && (
        <div>
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-5 h-5 rounded bg-[var(--card-hover)] flex items-center justify-center">
              <svg className="w-3 h-3 text-[var(--subtle)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
            </div>
            <span className="text-[10px] uppercase tracking-wider text-[var(--subtle)] font-semibold">Experience</span>
          </div>
          <div className="space-y-2 pl-7">
            {analysis.experience_entries!.map((entry, i) => (
              <div key={i} className="relative">
                {i < analysis.experience_entries!.length - 1 && (
                  <div className="absolute -left-[15px] top-4 bottom-0 w-px bg-white/6" />
                )}
                <div className="absolute -left-[18px] top-1.5 w-[7px] h-[7px] rounded-full border border-white/15 bg-[var(--bg)]" />
                <p className="text-xs font-medium text-[var(--fg)]">{entry.title}</p>
                <p className="text-[11px] text-[var(--subtle)]">
                  {entry.company}{entry.dates ? ` · ${entry.dates}` : ""}
                </p>
                {entry.summary && (
                  <p className="text-[11px] text-[var(--fg)]/50 mt-0.5">{entry.summary}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Education */}
      {hasEducation && (
        <div>
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-5 h-5 rounded bg-[var(--card-hover)] flex items-center justify-center">
              <svg className="w-3 h-3 text-[var(--subtle)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="m12 3-10 5 10 5 10-5z"/><path d="M20 8v7.5"/><path d="m6.53 9.22 0 6.28a5 5 0 0 0 10.94 0l0-6.28"/></svg>
            </div>
            <span className="text-[10px] uppercase tracking-wider text-[var(--subtle)] font-semibold">Education</span>
          </div>
          <div className="space-y-1.5 pl-7">
            {analysis.education!.map((edu, i) => (
              <div key={i}>
                <p className="text-xs font-medium text-[var(--fg)]">{edu.degree}</p>
                <p className="text-[11px] text-[var(--subtle)]">
                  {edu.institution}{edu.year ? ` · ${edu.year}` : ""}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Skills */}
      {hasSkills && (
        <div>
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-5 h-5 rounded bg-[var(--card-hover)] flex items-center justify-center">
              <svg className="w-3 h-3 text-[var(--subtle)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            </div>
            <span className="text-[10px] uppercase tracking-wider text-[var(--subtle)] font-semibold">Skills</span>
          </div>
          <div className="flex flex-wrap gap-1.5 pl-7">
            {analysis.skills!.map((skill, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.06] text-[11px] text-[var(--fg)]/70"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function CVCoachSection({ analysis }: { analysis: CVAnalysisResult }) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const hasProfile = analysis.candidate_name || analysis.current_role || analysis.education?.length || analysis.skills?.length;

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "fixes", label: `Fixes (${analysis.highlights.length})` },
    ...(hasProfile ? [{ key: "profile" as Tab, label: "Profile" }] : []),
  ];

  const criticalCount = analysis.highlights.filter((h) => h.severity === "critical").length;
  const importantCount = analysis.highlights.filter((h) => h.severity === "important").length;

  return (
    <section className="w-full mt-8 rounded-2xl border border-white/[0.08] bg-[var(--card)]/60 backdrop-blur-xl overflow-hidden">
      {/* Header with score */}
      <div className="px-6 py-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-5">
          <ScoreRing score={analysis.overall_score_0_100} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-display text-xl text-[var(--fg)]">CV Review</h3>
              {analysis.file_name && (
                <span className="text-[10px] text-[var(--subtle)] bg-white/[0.04] px-2 py-0.5 rounded-full truncate max-w-[140px]">
                  {analysis.file_name}
                </span>
              )}
            </div>
            <p className="text-sm text-[var(--fg)]/70 leading-relaxed">{analysis.overall_summary}</p>
            {(criticalCount > 0 || importantCount > 0) && (
              <div className="flex items-center gap-3 mt-2.5">
                {criticalCount > 0 && (
                  <span className="flex items-center gap-1.5 text-[11px] text-red-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                    {criticalCount} critical
                  </span>
                )}
                {importantCount > 0 && (
                  <span className="flex items-center gap-1.5 text-[11px] text-amber-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    {importantCount} important
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/[0.06] px-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`relative px-4 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? "text-[var(--fg)]"
                : "text-[var(--subtle)] hover:text-[var(--fg)]/70"
            }`}
          >
            {tab.label}
            {activeTab === tab.key && (
              <motion.div
                layoutId="cv-tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-px bg-[var(--gold)]"
                transition={{ duration: 0.2 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-6 py-5">
        <AnimatePresence mode="wait">
          {activeTab === "overview" && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="space-y-5"
            >
              {/* Strengths */}
              {analysis.strengths.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-green-400 font-semibold mb-2.5">
                    What&apos;s working
                  </p>
                  <div className="grid gap-2">
                    {analysis.strengths.map((s, i) => (
                      <div key={i} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-green-400/[0.04] border border-green-400/10">
                        <svg className="w-3.5 h-3.5 text-green-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                        <span className="text-xs text-[var(--fg)]/80">{s}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Key actions */}
              {analysis.top_actions.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--gold)] font-semibold mb-2.5">
                    Priority actions
                  </p>
                  <div className="space-y-1.5">
                    {analysis.top_actions.map((action, i) => {
                      const [issue, fix] = action.includes("→") ? action.split("→").map((s) => s.trim()) : [action, ""];
                      return (
                        <div key={i} className="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                          <span className="text-[var(--gold)] text-xs font-bold mt-px flex-shrink-0">{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-[var(--fg)]/80">{issue}</p>
                            {fix && <p className="text-[11px] text-[var(--gold)]/70 mt-0.5">{fix}</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Donald's take */}
              {analysis.coaching_notes && (
                <div className="rounded-xl bg-[var(--gold)]/[0.04] border border-[var(--gold)]/10 px-4 py-3.5">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-5 h-5 rounded-full bg-[var(--gold)]/15 flex items-center justify-center">
                      <span className="text-[10px] font-bold text-[var(--gold)]">D</span>
                    </div>
                    <span className="text-[10px] uppercase tracking-wider text-[var(--gold)] font-semibold">Donald&apos;s take</span>
                  </div>
                  <p className="text-sm text-[var(--fg)]/75 leading-relaxed italic">
                    &ldquo;{analysis.coaching_notes}&rdquo;
                  </p>
                </div>
              )}

              {/* Missing sections */}
              {analysis.sections && analysis.sections.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-red-300 font-semibold mb-2">
                    Missing from your CV
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.sections.map((sec: CVSectionFeedback, i: number) => (
                      <span key={i} className="px-2.5 py-1 rounded-lg bg-red-400/[0.06] border border-red-400/10 text-[11px] text-red-300">
                        {sec.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === "fixes" && (
            <motion.div
              key="fixes"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="space-y-3"
            >
              {analysis.highlights.map((h, i) => {
                const sev = SEVERITY_CONFIG[h.severity] ?? SEVERITY_CONFIG.suggestion;
                return (
                  <div key={i} className={`rounded-xl border ${sev.border} ${sev.bg} overflow-hidden`}>
                    <div className="px-4 py-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`w-2 h-2 rounded-full ${sev.dot}`} />
                        <span className="text-xs font-medium text-[var(--fg)]">{h.section}</span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${sev.badge} uppercase tracking-wider font-medium`}>
                          {sev.label}
                        </span>
                      </div>
                      <div className="grid md:grid-cols-2 gap-2.5">
                        <div className="rounded-lg bg-[var(--bg)]/60 border border-red-400/10 px-3 py-2.5">
                          <p className="text-[9px] uppercase tracking-wider text-red-300/70 font-medium mb-1">Current</p>
                          <p className="text-xs text-[var(--fg)]/70 leading-relaxed">{h.original_text}</p>
                        </div>
                        <div className="rounded-lg bg-[var(--bg)]/60 border border-green-400/10 px-3 py-2.5">
                          <p className="text-[9px] uppercase tracking-wider text-green-300/70 font-medium mb-1">Change to</p>
                          <p className="text-xs text-[var(--fg)]/85 leading-relaxed">{h.suggested_text}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {analysis.highlights.length === 0 && (
                <p className="text-xs text-[var(--subtle)] text-center py-6">No specific fixes identified.</p>
              )}

              {analysis.cv_text && analysis.highlights.length > 0 && (
                <div className="pt-2">
                  <AnnotatedCvText cvText={analysis.cv_text} highlights={analysis.highlights} />
                </div>
              )}
            </motion.div>
          )}

          {activeTab === "profile" && hasProfile && (
            <motion.div
              key="profile"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
            >
              <ProfileCard analysis={analysis} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
