"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadCV, type CVAnalysisResult, type CVFix } from "@/lib/api";

const SEV_STYLE: Record<string, { dot: string; label: string }> = {
  critical: { dot: "bg-[var(--red)]", label: "text-[var(--red)]" },
  important: { dot: "bg-[var(--gold)]", label: "text-[var(--gold)]" },
  suggestion: { dot: "bg-blue-400", label: "text-blue-400" },
};

export default function CVFeedback({ sessionId }: { sessionId?: string }) {
  const [phase, setPhase] = useState<"idle" | "uploading" | "done">("idle");
  const [analysis, setAnalysis] = useState<CVAnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError("");
      setPhase("uploading");
      try {
        const res = await uploadCV(file, sessionId);
        setAnalysis(res.analysis);
        setPhase("done");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        setPhase("idle");
      }
    },
    [sessionId],
  );

  if (phase === "idle") {
    return (
      <div
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border border-dashed p-5 text-center transition-all ${
          dragOver
            ? "border-[var(--gold)] bg-[var(--gold)]/5"
            : "border-white/10 bg-[var(--card)] hover:border-[var(--gold-dim)]"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
          className="hidden"
        />
        <p className="text-[var(--fg)] text-sm font-medium mb-0.5">
          Drop your CV for a quick roast
        </p>
        <p className="text-[var(--subtle)] text-xs">
          PDF, DOCX, or TXT — takes ~10s
        </p>
        {error && (
          <p className="text-[var(--red)] text-xs mt-2">{error}</p>
        )}
      </div>
    );
  }

  if (phase === "uploading") {
    return (
      <div className="rounded-xl border border-white/5 bg-[var(--card)] p-5 text-center">
        <div className="w-8 h-8 mx-auto mb-2 rounded-full border-2 border-transparent border-t-[var(--gold)] animate-spin" />
        <p className="text-[var(--subtle)] text-xs">Reading your CV…</p>
      </div>
    );
  }

  if (!analysis) return null;

  const scoreColor =
    analysis.overall_score_0_100 >= 70
      ? "text-green-400"
      : analysis.overall_score_0_100 >= 40
        ? "text-[var(--gold)]"
        : "text-[var(--red)]";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-white/5 bg-[var(--card)] overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-4 px-5 py-4 border-b border-white/5">
        <div className="text-center">
          <span className={`text-2xl font-bold ${scoreColor}`}>
            {analysis.overall_score_0_100}
          </span>
          <p className="text-[8px] text-[var(--subtle)] uppercase tracking-wider">
            score
          </p>
        </div>
        <p className="text-sm text-[var(--fg)]/80 flex-1">
          {analysis.overall_summary}
        </p>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Strengths */}
        {analysis.strengths.length > 0 && (
          <div>
            <p className="text-[10px] text-green-400 uppercase tracking-wider font-semibold mb-1.5">
              Strengths
            </p>
            <div className="flex flex-wrap gap-2">
              {analysis.strengths.map((s, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-full bg-green-500/10 text-green-400 text-xs"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Fixes */}
        <div>
          <p className="text-[10px] text-[var(--gold)] uppercase tracking-wider font-semibold mb-2">
            Fix these
          </p>
          <div className="space-y-2">
            {analysis.highlights.map((fix, i) => (
              <FixRow key={i} fix={fix} />
            ))}
          </div>
        </div>

        {/* Donald's take */}
        {analysis.coaching_notes && (
          <div className="pt-2 border-t border-white/5">
            <p className="text-[10px] text-[var(--subtle)] uppercase tracking-wider font-semibold mb-1">
              Donald says
            </p>
            <p className="text-sm text-[var(--fg)]/70 leading-relaxed italic">
              &ldquo;{analysis.coaching_notes}&rdquo;
            </p>
          </div>
        )}
      </div>

      {/* Upload another */}
      <button
        onClick={() => {
          setPhase("idle");
          setAnalysis(null);
        }}
        className="w-full py-2.5 text-xs text-[var(--subtle)] hover:text-[var(--fg)] border-t border-white/5 transition-colors"
      >
        Upload another CV
      </button>
    </motion.div>
  );
}

function FixRow({ fix }: { fix: CVFix }) {
  const sev = SEV_STYLE[fix.severity] ?? SEV_STYLE.suggestion;
  return (
    <div className="flex items-start gap-2.5">
      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${sev.dot}`} />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[var(--fg)]/80">
          <span className={`font-medium ${sev.label}`}>{fix.section}</span>
          {" — "}
          {fix.original_text}
        </p>
        <p className="text-xs text-[var(--subtle)] mt-0.5">
          → {fix.suggested_text}
        </p>
      </div>
    </div>
  );
}
