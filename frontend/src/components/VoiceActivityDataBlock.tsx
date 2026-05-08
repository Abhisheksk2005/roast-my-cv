"use client";

import type { VoiceActivityRow } from "./VoiceActivityPanel";

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string");
}

/** Friendly breakdown of webhook research payloads for the live feed. */
export default function VoiceActivityDataBlock({ row }: { row: VoiceActivityRow }) {
  const d = row.data;
  if (!d || typeof d !== "object") return null;

  const queries = asStringArray((d as Record<string, unknown>).queries);
  const step = (d as Record<string, unknown>).step;

  if (queries.length === 0 && step !== "research_complete") return null;

  if (step === "research_complete") {
    return (
      <div className="mt-2 pt-2 border-t border-white/5 space-y-2 text-[11px] text-[var(--subtle)] leading-snug">
        <p className="text-[var(--subtle)]/90 font-light">
          Numbers are back. Donald has the snapshot and will do the roast now.
        </p>
      </div>
    );
  }

  const maxList = 6;
  const shown = queries.slice(0, maxList);
  const rest = queries.length - shown.length;
  const queryCount = typeof (d as { query_count?: number }).query_count === "number"
    ? (d as { query_count: number }).query_count
    : queries.length;

  return (
    <div className="mt-2 pt-2 border-t border-white/5 space-y-2.5 text-[11px] text-[var(--subtle)] leading-snug">
      {step === "research_started" && (
        <p className="text-[var(--subtle)]/90 font-light">
          {(d as { note?: string }).note ||
            "We’re gathering public info so Donald’s roast is based on real numbers."}
        </p>
      )}

      {queries.length > 0 && step === "research_started" && (
        <div>
          <p className="text-[10px] font-semibold text-[var(--fg)]/80 uppercase tracking-wider mb-1.5">
            Sample lookups ({queryCount})
          </p>
          <ul className="space-y-1 pl-0.5">
            {shown.map((q, i) => (
              <li key={i} className="flex gap-2 break-words">
                <span className="text-[var(--gold)]/70 shrink-0">·</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
          {rest > 0 ? (
            <p className="text-[10px] text-[var(--subtle)]/60 mt-1.5">...and {rest} more checks</p>
          ) : null}
        </div>
      )}

    </div>
  );
}
