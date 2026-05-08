"use client";

import { useState } from "react";
import type { CVFix } from "@/lib/api";

type Span =
  | { type: "text"; value: string }
  | { type: "mark"; value: string; fix: CVFix };

function findFirstMatch(haystack: string, needle: string): { start: number; end: number } | null {
  if (!needle) return null;
  const at = haystack.indexOf(needle);
  if (at === -1) return null;
  return { start: at, end: at + needle.length };
}

const SEVERITY_STYLE: Record<string, { ring: string; bg: string; text: string; label: string }> = {
  critical: { ring: "ring-red-400/40", bg: "bg-red-400/10", text: "text-red-300", label: "Critical" },
  important: { ring: "ring-amber-400/40", bg: "bg-amber-400/10", text: "text-amber-300", label: "Important" },
  suggestion: { ring: "ring-blue-400/30", bg: "bg-blue-400/8", text: "text-blue-300", label: "Suggestion" },
};

function FixTooltip({ fix, onClose }: { fix: CVFix; onClose: () => void }) {
  const sev = SEVERITY_STYLE[fix.severity] ?? SEVERITY_STYLE.suggestion;
  return (
    <div
      className="absolute z-30 left-0 right-0 md:left-auto md:right-auto md:w-80 mt-1 rounded-xl border border-white/10 bg-[var(--card)] shadow-2xl shadow-black/40 p-3.5"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${sev.bg} ${sev.text} uppercase tracking-wider font-medium border border-white/5`}>
            {sev.label}
          </span>
          <span className="text-[11px] text-[var(--subtle)] font-medium">{fix.section}</span>
        </div>
        <button onClick={onClose} className="text-[var(--subtle)] hover:text-[var(--fg)] transition-colors p-0.5">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div className="space-y-2">
        <div className="rounded-lg bg-red-400/[0.05] border border-red-400/10 px-2.5 py-2">
          <p className="text-[9px] uppercase tracking-wider text-red-300/60 font-medium mb-0.5">Current</p>
          <p className="text-[11px] text-[var(--fg)]/70 leading-relaxed">{fix.original_text}</p>
        </div>
        <div className="rounded-lg bg-green-400/[0.05] border border-green-400/10 px-2.5 py-2">
          <p className="text-[9px] uppercase tracking-wider text-green-300/60 font-medium mb-0.5">Suggested</p>
          <p className="text-[11px] text-[var(--fg)]/85 leading-relaxed">{fix.suggested_text}</p>
        </div>
      </div>
    </div>
  );
}

export default function AnnotatedCvText({
  cvText,
  highlights,
}: {
  cvText: string;
  highlights: CVFix[];
}) {
  const [activeFix, setActiveFix] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);

  const matches: { start: number; end: number; fix: CVFix; idx: number }[] = [];
  for (let idx = 0; idx < highlights.length; idx++) {
    const fix = highlights[idx];
    const needle = (fix.original_text || "").trim();
    if (!needle) continue;
    const m = findFirstMatch(cvText, needle);
    if (!m) continue;
    matches.push({ start: m.start, end: m.end, fix, idx });
  }
  matches.sort((a, b) => a.start - b.start);

  const nonOverlapping: typeof matches = [];
  let cursor = -1;
  for (const m of matches) {
    if (m.start < cursor) continue;
    nonOverlapping.push(m);
    cursor = m.end;
  }

  const spans: (Span & { idx?: number })[] = [];
  let pos = 0;
  for (const m of nonOverlapping) {
    if (m.start > pos) spans.push({ type: "text", value: cvText.slice(pos, m.start) });
    spans.push({ type: "mark", value: cvText.slice(m.start, m.end), fix: m.fix, idx: m.idx });
    pos = m.end;
  }
  if (pos < cvText.length) spans.push({ type: "text", value: cvText.slice(pos) });

  const sevColor = (sev: string) => {
    if (sev === "critical") return "decoration-red-400/60 bg-red-400/[0.08]";
    if (sev === "important") return "decoration-amber-400/60 bg-amber-400/[0.08]";
    return "decoration-blue-400/50 bg-blue-400/[0.06]";
  };

  const maxHeight = expanded ? "max-h-none" : "max-h-[320px]";
  const needsExpand = cvText.length > 1500;

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[var(--bg)]/30 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[var(--subtle)] font-semibold">Annotated CV</p>
          <p className="text-[11px] text-[var(--subtle)]/70 mt-0.5">
            Click highlights to see suggestions
          </p>
        </div>
        <div className="flex items-center gap-3">
          {nonOverlapping.length > 0 && (
            <span className="text-[10px] text-[var(--subtle)] bg-white/[0.04] px-2 py-0.5 rounded-full">
              {nonOverlapping.length} annotation{nonOverlapping.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
      <div className={`${maxHeight} overflow-auto p-4 relative`} onClick={() => setActiveFix(null)}>
        <div className="text-[12.5px] leading-[1.85] text-[var(--fg)]/75 whitespace-pre-wrap break-words font-[system-ui]">
          {spans.map((s, i) => {
            if (s.type === "text") return <span key={i}>{s.value}</span>;
            const isActive = activeFix === s.idx;
            return (
              <span key={i} className="relative inline">
                <mark
                  className={`rounded-sm px-0.5 py-px cursor-pointer transition-all underline underline-offset-2 decoration-wavy ${sevColor(s.fix.severity)} ${
                    isActive ? "ring-1 ring-[var(--gold)]/40" : "hover:ring-1 hover:ring-white/10"
                  } text-[var(--fg)]/85`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveFix(isActive ? null : s.idx ?? null);
                  }}
                >
                  {s.value}
                </mark>
                {isActive && (
                  <FixTooltip fix={s.fix} onClose={() => setActiveFix(null)} />
                )}
              </span>
            );
          })}
        </div>
        {!expanded && needsExpand && (
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-[var(--bg)]/90 to-transparent pointer-events-none" />
        )}
      </div>
      {needsExpand && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="w-full py-2 text-[11px] text-[var(--subtle)] hover:text-[var(--fg)] border-t border-white/[0.04] transition-colors"
        >
          Show full CV
        </button>
      )}
    </div>
  );
}
