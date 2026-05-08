"use client";

const SEV_COLORS: Record<string, { dot: string; text: string; bg: string }> = {
  critical: { dot: "bg-red-400", text: "text-red-400", bg: "bg-red-400/10" },
  important: { dot: "bg-amber-400", text: "text-amber-400", bg: "bg-amber-400/10" },
  suggestion: { dot: "bg-blue-400", text: "text-blue-400", bg: "bg-blue-400/10" },
};

type Fix = {
  original_text?: string;
  suggested_text?: string;
  severity?: string;
  section?: string;
};

type Education = { degree?: string; institution?: string; year?: string };

export default function CvAnalysisBlock({ analysis }: { analysis: Record<string, unknown> }) {
  const score = typeof analysis.overall_score_0_100 === "number" ? analysis.overall_score_0_100 : null;
  const verdict = typeof analysis.overall_summary === "string" ? analysis.overall_summary : "";
  const name = typeof analysis.candidate_name === "string" ? analysis.candidate_name : "";
  const role = typeof analysis.current_role === "string" ? analysis.current_role : "";
  const company = typeof analysis.current_company === "string" ? analysis.current_company : "";
  const strengths = Array.isArray(analysis.strengths) ? (analysis.strengths as string[]) : [];
  const skills = Array.isArray(analysis.skills) ? (analysis.skills as string[]).slice(0, 6) : [];
  const education = Array.isArray(analysis.education) ? (analysis.education as Education[]) : [];
  const fixes = Array.isArray(analysis.highlights) ? (analysis.highlights as Fix[]) : [];
  const donaldTake = typeof analysis.coaching_notes === "string" ? analysis.coaching_notes : "";

  const scoreColor =
    score !== null && score >= 70 ? "text-green-400" : score !== null && score >= 40 ? "text-amber-400" : "text-red-400";
  const scoreBarPct = score !== null ? Math.min(100, Math.max(0, score)) : 0;
  const scoreBarColor =
    score !== null && score >= 70 ? "bg-green-400" : score !== null && score >= 40 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="mt-2.5 pt-2.5 border-t border-white/5 space-y-3">
      {/* Profile quick info */}
      {(name || role) && (
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-[var(--gold)]/10 border border-[var(--gold)]/20 flex items-center justify-center flex-shrink-0">
            <span className="text-[10px] font-semibold text-[var(--gold)]">{(name || "?")[0]?.toUpperCase()}</span>
          </div>
          <div className="min-w-0">
            {name && <p className="text-[11px] font-medium text-[var(--fg)] truncate">{name}</p>}
            {(role || company) && (
              <p className="text-[10px] text-[var(--subtle)] truncate">
                {[role, company].filter(Boolean).join(" at ")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Score + verdict */}
      {score !== null && (
        <div>
          <div className="flex items-center gap-3 mb-1.5">
            <span className={`text-xl font-bold leading-none ${scoreColor}`}>{score}</span>
            <span className="text-[10px] text-[var(--subtle)] uppercase tracking-wider">/100</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div
              className={`h-full rounded-full ${scoreBarColor} transition-all duration-500`}
              style={{ width: `${scoreBarPct}%` }}
            />
          </div>
          {verdict && (
            <p className="text-[11px] text-[var(--fg)]/80 font-medium leading-snug">{verdict}</p>
          )}
        </div>
      )}

      {/* Strengths */}
      {strengths.length > 0 && (
        <div>
          <p className="text-[10px] text-green-400 uppercase tracking-wider font-semibold mb-1">Strengths</p>
          <div className="flex flex-wrap gap-1.5">
            {strengths.map((s, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 text-[10px]">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Skills (compact) */}
      {skills.length > 0 && (
        <div>
          <p className="text-[10px] text-[var(--subtle)] uppercase tracking-wider font-semibold mb-1">Key skills</p>
          <div className="flex flex-wrap gap-1">
            {skills.map((s, i) => (
              <span key={i} className="px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-[9px] text-[var(--fg)]/60">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Education (compact) */}
      {education.length > 0 && (
        <div>
          <p className="text-[10px] text-[var(--subtle)] uppercase tracking-wider font-semibold mb-1">Education</p>
          {education.slice(0, 2).map((edu, i) => (
            <p key={i} className="text-[10px] text-[var(--fg)]/60">
              {edu.degree}{edu.institution ? ` — ${edu.institution}` : ""}{edu.year ? ` (${edu.year})` : ""}
            </p>
          ))}
        </div>
      )}

      {/* Fixes */}
      {fixes.length > 0 && (
        <div>
          <p className="text-[10px] text-amber-400 uppercase tracking-wider font-semibold mb-1.5">Fix these</p>
          <div className="space-y-1.5">
            {fixes.map((fix, i) => {
              const sev = SEV_COLORS[fix.severity || "suggestion"] || SEV_COLORS.suggestion;
              return (
                <div key={i} className={`rounded-lg px-2.5 py-2 ${sev.bg} border border-white/5`}>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${sev.dot}`} />
                    <span className={`text-[10px] font-semibold uppercase tracking-wider ${sev.text}`}>
                      {fix.section}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--fg)]/80 leading-snug">{fix.original_text}</p>
                  {fix.suggested_text && (
                    <p className="text-[11px] text-[var(--subtle)] leading-snug mt-0.5">
                      &rarr; {fix.suggested_text}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Donald's take */}
      {donaldTake && (
        <div className="pt-1.5 border-t border-white/5">
          <p className="text-[10px] text-[var(--subtle)] uppercase tracking-wider font-semibold mb-1">Donald says</p>
          <p className="text-[11px] text-[var(--fg)]/70 leading-relaxed italic">
            &ldquo;{donaldTake}&rdquo;
          </p>
        </div>
      )}
    </div>
  );
}
