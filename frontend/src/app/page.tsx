"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import HeroBackground from "@/components/HeroBackground";
import FeaturesSection from "@/components/FeaturesSection";
import StatsSection from "@/components/StatsSection";
import WalkthroughSection from "@/components/WalkthroughSection";
import BubblyVoiceAnimation from "@/components/BubblyVoiceAnimation";
import TestimonialsSection from "@/components/TestimonialsSection";
import CTASection from "@/components/CTASection";
import Footer from "@/components/Footer";
import { BurningCapIcon } from "@/components/icons";

const headlineEase = [0.22, 1, 0.36, 1] as [number, number, number, number];

function AnimatedHeadline() {
  const line1 = ["Is", "AI", "coming", "for", "your", "job?"];
  const line2 = ["Find", "out.", "Then", "career", "max."];
  const gradientWords = new Set(["job?", "max."]);

  const renderWords = (words: string[], baseDelay: number) =>
    words.map((word, i) => {
      const w = word.toLowerCase();
      const isAccent = gradientWords.has(w);
      return (
        <motion.span
          key={`${baseDelay}-${i}-${word}`}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: baseDelay + i * 0.06, ease: headlineEase }}
          className={`inline-block mr-[0.2em] last:mr-0 ${isAccent ? "text-gradient" : ""}`}
        >
          {isAccent ? <em>{word}</em> : word}
        </motion.span>
      );
    });

  return (
    <h1 className="font-display leading-[1.02] tracking-tight text-center lg:text-left">
      <span className="block text-5xl sm:text-6xl md:text-7xl lg:text-8xl">{renderWords(line1, 0.35)}</span>
      <span className="block mt-3 text-[clamp(1.65rem,4.5vw,3.75rem)] text-white/90">
        {renderWords(line2, 0.35 + line1.length * 0.06 + 0.12)}
      </span>
    </h1>
  );
}

export default function Home() {
  const router = useRouter();

  return (
    <main className="overflow-x-hidden">
      <Navbar />

      {/* ===== HERO ===== */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-20 pb-28 overflow-hidden">
        <HeroBackground />
        <div className="relative z-10 w-full max-w-6xl mx-auto grid lg:grid-cols-[1fr_1.05fr] gap-12 lg:gap-8 items-center">
          <div className="text-center lg:text-left">
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}
              className="inline-flex items-center gap-2.5 mb-8 lg:mx-0 mx-auto">
              <BurningCapIcon size={24} className="text-[var(--gold)]" />
              <span className="text-xs font-semibold tracking-[0.2em] uppercase text-[var(--subtle)]">The Degree Verdict</span>
            </motion.div>

            <AnimatedHeadline />

            <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 1.0 }}
              className="mt-6 text-[var(--subtle)] text-sm md:text-base max-w-md mx-auto lg:mx-0 font-light leading-relaxed">
              Donald roasts your degree with receipts, then tells you how to career max and stay ahead of AI. <span className="text-[var(--gold)]">No signup.</span>
            </motion.p>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 1.25 }}
              className="mt-8 flex flex-col items-center lg:items-start gap-3">
              <motion.button
                onClick={() => router.push("/roast")}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="px-10 py-4 bg-[var(--gold)] text-black font-bold text-base rounded-xl hover:bg-[var(--gold-dim)] transition-colors glow-gold"
              >
                Get Started
              </motion.button>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="relative w-full flex justify-center lg:justify-end"
          >
            <BubblyVoiceAnimation />
          </motion.div>
        </div>

        {/* Scroll hint */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.4 }} transition={{ delay: 2.5, duration: 0.8 }}
          className="absolute bottom-6 left-1/2 -translate-x-1/2">
          <div className="w-5 h-8 rounded-full border border-white/20 flex items-start justify-center p-1.5 animate-bounce">
            <div className="w-1 h-1.5 rounded-full bg-white/40" />
          </div>
        </motion.div>
      </section>

      <StatsSection />
      <WalkthroughSection />
      <FeaturesSection />
      <TestimonialsSection />
      <CTASection />
      <Footer />
    </main>
  );
}
