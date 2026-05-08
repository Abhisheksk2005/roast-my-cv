"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getDegreeTier } from "@/lib/degreeTier";
import { getPublicReviews, type PublicReview } from "@/lib/api";

const FALLBACK_TESTIMONIALS = [
  { quote: "$180k degree, AI writes better essays. The numbers broke me.", reviewer_name: "Sarah M.", degree: "English Lit", university: "NYU", grade: "D" },
  { quote: "67% automation risk + 90s of salary truth. Unwell.", reviewer_name: "Marcus T.", degree: "Comms", university: "USC", grade: "F" },
  { quote: "CS degree, low replace risk. I'll take it.", reviewer_name: "Priya K.", degree: "CS", university: "Georgia Tech", grade: "A" },
];

export default function TestimonialsSection() {
  const [testimonials, setTestimonials] = useState<PublicReview[]>([]);

  useEffect(() => {
    let mounted = true;
    getPublicReviews(20).then((rows) => {
      if (!mounted) return;
      if (rows.length > 0) {
        setTestimonials(rows);
      } else {
        setTestimonials(
          FALLBACK_TESTIMONIALS.map((t, i) => ({
            review_id: `fallback-${i}`,
            session_id: `fallback-session-${i}`,
            quote: t.quote,
            reviewer_name: t.reviewer_name,
            degree: t.degree,
            university: t.university,
            grade: t.grade,
            grade_score: 0,
            created_at: new Date().toISOString(),
          }))
        );
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.6 }} className="text-center mb-12">
          <span className="text-[var(--subtle)] text-xs font-semibold tracking-[0.2em] uppercase">Survivors</span>
          <h2 className="font-display text-3xl md:text-4xl mt-2">The <em>aftermath</em></h2>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => {
            const tier = getDegreeTier(t.grade);
            return (
            <motion.div key={t.review_id} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative p-7 rounded-2xl bg-[var(--card)] border border-white/5 overflow-visible">
              <div
                className={`absolute -top-2 right-3 rounded-xl px-2.5 py-1.5 flex items-center justify-center font-bold font-display border-2 bg-[var(--bg)] text-center leading-tight ${
                  tier.badge.length > 10 ? "max-w-[10.5rem] text-[9px]" : "min-w-[3.25rem] text-xs"
                }`}
                style={{ borderColor: tier.color, color: tier.color }}>{tier.badge}</div>
              <p className="font-display italic text-sm leading-relaxed mb-5">&ldquo;{t.quote}&rdquo;</p>
              <p className="text-sm font-semibold">{t.reviewer_name}</p>
              <p className="text-[var(--subtle)] text-xs mt-0.5">{t.degree} — {t.university}</p>
            </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
