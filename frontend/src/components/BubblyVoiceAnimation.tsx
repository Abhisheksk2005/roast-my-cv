"use client";

import { motion } from "framer-motion";

const BUBBLES = [
  { size: 56, x: "8%", y: "12%", delay: 0, duration: 5.2 },
  { size: 36, x: "78%", y: "18%", delay: 0.4, duration: 4.4 },
  { size: 44, x: "6%", y: "62%", delay: 0.2, duration: 5.8 },
  { size: 28, x: "88%", y: "58%", delay: 0.6, duration: 4.1 },
  { size: 22, x: "42%", y: "8%", delay: 0.1, duration: 3.9 },
  { size: 32, x: "52%", y: "78%", delay: 0.5, duration: 5.1 },
];

const BAR_PATTERN = [0.35, 0.85, 0.55, 1, 0.7, 0.45, 0.9, 0.6] as const;

export default function BubblyVoiceAnimation() {
  return (
    <div className="relative w-full max-w-[min(100%,380px)] mx-auto aspect-square md:aspect-[5/4]">
      {/* Floating bubbles */}
      {BUBBLES.map((b, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full pointer-events-none"
          style={{
            width: b.size,
            height: b.size,
            left: b.x,
            top: b.y,
            background:
              "radial-gradient(circle at 30% 30%, rgba(245,166,35,0.35), rgba(230,57,70,0.12) 55%, transparent 70%)",
            boxShadow: "inset 0 0 20px rgba(255,255,255,0.06), 0 0 40px rgba(245,166,35,0.08)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{
            opacity: [0.45, 0.85, 0.5, 0.8, 0.45],
            y: [0, -14, 4, -10, 0],
            x: [0, 6, -4, 5, 0],
            scale: [1, 1.06, 0.98, 1.04, 1],
          }}
          transition={{
            duration: b.duration,
            delay: b.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}

      {/* Center card: voice + mini bubble */}
      <div className="absolute inset-[18%] rounded-[2rem] border border-white/10 bg-[var(--card)]/80 backdrop-blur-md flex flex-col items-center justify-center gap-6 shadow-[0_0_80px_rgba(245,166,35,0.06)]">
        <motion.div
          className="absolute -right-2 -top-3 px-3 py-1.5 rounded-2xl rounded-bl-md border border-white/10 bg-[var(--bg)]/90 text-[10px] font-semibold tracking-widest uppercase text-[var(--gold)]"
          animate={{ y: [0, -4, 0], scale: [1, 1.02, 1] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        >
          Live advice
        </motion.div>

        <div className="flex h-14 items-end justify-center gap-1.5 px-4">
          {BAR_PATTERN.map((peak, i) => (
            <motion.div
              key={i}
              className="w-2 max-h-full rounded-full origin-bottom"
              style={{
                background: "linear-gradient(180deg, var(--gold) 0%, var(--red-deep) 100%)",
                height: Math.round(52 * peak),
              }}
              animate={{
                scaleY: [0.35, 1, 0.5, 0.92, 0.4, 0.78, 0.35],
              }}
              transition={{
                duration: 0.9 + (i % 3) * 0.12,
                repeat: Infinity,
                ease: [0.45, 0, 0.55, 1],
                delay: i * 0.08,
              }}
            />
          ))}
        </div>

        <motion.div
          className="flex gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {[0, 1, 2].map((j) => (
            <motion.span
              key={j}
              className="w-2 h-2 rounded-full bg-[var(--gold)]/70"
              animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
              transition={{
                duration: 0.9,
                repeat: Infinity,
                delay: j * 0.15,
                ease: "easeInOut",
              }}
            />
          ))}
        </motion.div>
      </div>
    </div>
  );
}
