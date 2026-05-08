"use client";

import { motion } from "framer-motion";
import { useState } from "react";

import { getDegreeTier } from "@/lib/degreeTier";

export default function ShareButtons({ sessionId, grade }: { sessionId: string; grade: string }) {
  const [copied, setCopied] = useState(false);
  const url = typeof window !== "undefined" ? `${window.location.origin}/report/${sessionId}` : "";
  const tier = getDegreeTier(grade);
  const text = `Donald labeled my degree "${tier.badge}" (AI job risk). yours?`;

  const copy = async () => { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 2 }}
      className="flex flex-wrap gap-2.5 justify-center">
      {[
        { name: "X", href: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text + " @firecrawl @elevenlabs #ElevenHacks")}&url=${encodeURIComponent(url)}` },
        { name: "LinkedIn", href: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}` },
      ].map((l) => (
        <a key={l.name} href={l.href} target="_blank" rel="noopener noreferrer"
          className="px-5 py-2.5 bg-[var(--card)] border border-white/8 hover:border-white/15 rounded-lg text-sm font-medium hover:bg-[var(--card-hover)] transition-all">
          Share on {l.name}
        </a>
      ))}
      <button onClick={copy}
        className="px-5 py-2.5 bg-[var(--card)] border border-white/8 hover:border-white/15 rounded-lg text-sm font-medium hover:bg-[var(--card-hover)] transition-all">
        {copied ? "Copied!" : "Copy Link"}
      </button>
    </motion.div>
  );
}
