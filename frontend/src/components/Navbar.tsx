"use client";

import { motion } from "framer-motion";
import { DonaldLogo } from "./icons";

export default function Navbar() {
  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 bg-[var(--bg)]/80 backdrop-blur-xl border-b border-white/5"
    >
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2 group">
          <DonaldLogo className="text-[var(--gold)] transition-transform group-hover:scale-110" />
          <span className="font-display text-lg text-[var(--fg)]">Donald</span>
        </a>
        <a
          href="/roast"
          className="px-5 py-2 text-sm font-semibold bg-[var(--gold)] text-black rounded-full
                     hover:bg-[var(--gold-dim)] transition-all glow-gold hover:scale-105 active:scale-95"
        >
          Talk to Donald
        </a>
      </div>
    </motion.nav>
  );
}
