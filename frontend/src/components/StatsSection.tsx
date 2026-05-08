"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getPublicMetrics } from "@/lib/api";

const STAT_LABELS = [
  "Degrees Cooked",
  "People Talked to Donald",
  "Got a C or Worse",
  "Tuition in Shambles",
  "Regret Score",
] as const;

export default function StatsSection() {
  const [stats, setStats] = useState<{ value: string; label: string }[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    getPublicMetrics()
      .then((m) => {
        if (!active) return;
        setStats([
          { value: m.display.degrees_cooked, label: "Degrees Cooked" },
          { value: m.display.people_talked_to_donald, label: "People Talked to Donald" },
          { value: m.display.c_or_worse_pct, label: "Got a C or Worse" },
          { value: m.display.tuition_in_shambles, label: "Tuition in Shambles" },
          { value: m.display.regret_score, label: "Regret Score" },
        ]);
        setStatus("ready");
      })
      .catch(() => {
        if (!active) return;
        setStatus("error");
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleStats =
    status === "ready"
      ? stats
      : STAT_LABELS.map((label) => ({
          label,
          value: status === "loading" ? "Loading..." : "Unavailable",
        }));

  return (
    <section className="py-20 px-6 border-y border-white/5">
      <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-8">
        {visibleStats.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.08 }}
            className="text-center">
            <div className="font-display text-3xl md:text-4xl text-gradient">{s.value}</div>
            <p className="text-[var(--subtle)] text-xs font-medium tracking-wide uppercase mt-1.5">{s.label}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
