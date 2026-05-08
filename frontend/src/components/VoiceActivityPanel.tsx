"use client";

import { useEffect, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { filterActivityForFeed } from "@/lib/voiceActivityFilter";
import VoiceActivityDataBlock from "@/components/VoiceActivityDataBlock";
import CvAnalysisBlock from "@/components/CvAnalysisBlock";
import { isVoiceResearchInProgress } from "@/lib/voiceActivityResearch";

export type VoiceActivityRow = {
  id: string;
  ts: number;
  source: "live" | "server";
  event: string;
  title: string;
  detail?: string;
  data?: Record<string, unknown> | null;
};

function eventIcon(event: string) {
  if (event.includes("cv")) return "\ud83d\udcc4";
  if (event.includes("research")) return "\ud83d\udd0e";
  if (event.includes("profile") || event.includes("user_profile")) return "\ud83d\udc64";
  if (event.includes("tool")) return "\u26a1";
  if (event.includes("transcript") || event.includes("message")) return "\ud83d\udcac";
  if (event === "error" || event === "disconnect") return "\u26a0\ufe0f";
  if (event.includes("connect") || event.includes("status")) return "\ud83d\udce1";
  if (event.includes("mode")) return "\ud83c\udf99\ufe0f";
  return "\u2726";
}

type PanelProps = {
  items: VoiceActivityRow[];
  pollOk?: boolean;
  pollError?: string;
  pollAt?: number;
};

export default function VoiceActivityPanel({
  items,
  pollOk = true,
  pollError,
  pollAt = 0,
}: PanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const visibleItems = useMemo(() => filterActivityForFeed(items), [items]);
  const researchRunning = useMemo(() => isVoiceResearchInProgress(items), [items]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleItems.length, researchRunning]);

  return (
    <aside
      className="w-full lg:max-h-[min(72vh,640px)] flex flex-col rounded-2xl border border-white/10 bg-[var(--card)]/80 backdrop-blur-md shadow-xl shadow-black/30 overflow-hidden text-left"
      aria-label="What happened on your call"
    >
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between gap-2">
        <div>
          <h2 className="font-display text-sm tracking-wide text-[var(--fg)]">Live feed</h2>
          <p className="text-[10px] text-[var(--subtle)] font-light">
            Your side of the chat and the facts Donald pulled for your roast.
          </p>
          {!pollOk && pollError ? (
            <p className="text-[10px] text-red-400/90 mt-1.5 leading-snug">
              Couldn&apos;t refresh for a moment — check your connection.
            </p>
          ) : pollAt > 0 && pollOk ? (
            <p className="text-[10px] text-[var(--subtle)]/70 mt-1">Keeping this list up to date.</p>
          ) : null}
        </div>
        <span className="text-[10px] uppercase tracking-wider text-[var(--gold)]/90 shrink-0">
          {visibleItems.length}
        </span>
      </div>

      <AnimatePresence>
        {researchRunning ? (
          <motion.div
            key="research-progress"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="border-b border-[var(--gold)]/20 bg-[var(--gold)]/[0.06] overflow-hidden"
            role="status"
            aria-live="polite"
            aria-label="Research in progress"
          >
            <div className="px-4 py-3">
              <div className="flex items-center gap-2.5 mb-2.5">
                <span
                  className="w-4 h-4 shrink-0 rounded-full border-2 border-[var(--gold)]/25 border-t-[var(--gold)] animate-spin"
                  aria-hidden
                />
                <div>
                  <p className="text-xs font-medium text-[var(--fg)] leading-snug">Pulling your numbers…</p>
                  <p className="text-[10px] text-[var(--subtle)] font-light mt-0.5 leading-relaxed">
                    Salaries, tuition, job market — usually under a minute. You can keep talking or wait here.
                  </p>
                </div>
              </div>
              <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                <motion.div
                  className="absolute top-0 h-full w-[40%] rounded-full bg-[var(--gold)] shadow-[0_0_12px_rgba(245,166,35,0.35)]"
                  animate={{ left: ["-40%", "105%"] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                    repeatDelay: 0.2,
                  }}
                />
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        <AnimatePresence initial={false}>
          {visibleItems.length === 0 ? (
            <p className="text-xs text-[var(--subtle)]/70 font-light px-1 py-6 text-center">
              When you speak, what you said and the stats Donald finds will show up here.
            </p>
          ) : (
            visibleItems.map((row) => (
              <motion.div
                key={row.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="rounded-xl border border-white/5 bg-[var(--bg)]/40 px-3 py-2.5"
              >
                <div className="flex items-start gap-2">
                  <span className="text-base leading-none mt-0.5 shrink-0" aria-hidden>
                    {eventIcon(row.event)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium text-[var(--fg)] leading-snug">{row.title}</span>
                    </div>
                    {row.detail ? (
                      <p className="text-[11px] text-[var(--subtle)] font-light mt-1 leading-relaxed whitespace-pre-wrap break-words">
                        {row.detail}
                      </p>
                    ) : null}
                    {(row.event === "webhook_research_started" || row.event === "webhook_research_complete") &&
                    row.data ? (
                      <VoiceActivityDataBlock row={row} />
                    ) : null}
                    {row.event === "cv_ready" && row.data?.cv_analysis ? (
                      <CvAnalysisBlock analysis={row.data.cv_analysis as Record<string, unknown>} />
                    ) : null}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}
