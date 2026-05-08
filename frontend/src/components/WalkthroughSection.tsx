"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { MicIcon, ChartDownIcon, GavelIcon } from "./icons";

const steps = [
  {
    icon: MicIcon,
    title: "You talk",
    hint: "Degree · school · vibe",
    color: "var(--gold)",
  },
  {
    icon: ChartDownIcon,
    title: "Donald digs",
    hint: "Salary · AI risk · market",
    color: "var(--red)",
  },
  {
    icon: GavelIcon,
    title: "Roast + game plan",
    hint: "Verdict · career moves",
    color: "var(--gold)",
  },
];

export default function WalkthroughSection() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const lineScale = useTransform(scrollYProgress, [0.15, 0.55], [0.15, 1]);

  return (
    <section ref={ref} className="py-24 md:py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.55 }}
          className="text-center mb-14 md:mb-20"
        >
          <span className="text-[var(--red)] text-xs font-semibold tracking-[0.2em] uppercase">How it works</span>
          <h2 className="font-display text-3xl md:text-5xl mt-2">Three beats. <em>One game plan.</em></h2>
        </motion.div>

        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-6">
          {/* Progress line (desktop) */}
          <div className="hidden md:block absolute top-[52px] left-[16%] right-[16%] h-px bg-white/10 overflow-hidden rounded-full pointer-events-none">
            <motion.div
              className="h-full origin-left bg-gradient-to-r from-[var(--gold)] via-[var(--red)] to-[var(--gold)]"
              style={{ scaleX: lineScale }}
            />
          </div>

          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.5, delay: i * 0.12, ease: [0.22, 1, 0.36, 1] }}
              className="relative flex flex-col items-center text-center"
            >
              <motion.div
                className="relative z-10 mb-5 flex h-[104px] w-[104px] items-center justify-center rounded-3xl border border-white/10 bg-[var(--card)] shadow-[0_20px_60px_rgba(0,0,0,0.35)]"
                style={{ color: step.color }}
                whileHover={{ y: -6, scale: 1.02 }}
                transition={{ type: "spring", stiffness: 380, damping: 22 }}
              >
                <motion.div
                  className="absolute inset-2 rounded-2xl opacity-40"
                  style={{
                    background: `radial-gradient(circle at 30% 20%, ${step.color}, transparent 65%)`,
                  }}
                  animate={{ opacity: [0.25, 0.45, 0.25] }}
                  transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
                />
                <step.icon size={40} className="relative z-10" />
                <span className="absolute -bottom-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--bg)] text-xs font-bold font-display border border-white/10">
                  {i + 1}
                </span>
              </motion.div>
              <h3 className="font-display text-xl md:text-2xl mb-1">{step.title}</h3>
              <p className="text-[var(--subtle)] text-sm font-light tracking-wide">{step.hint}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
