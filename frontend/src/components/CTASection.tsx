"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

export default function CTASection() {
  const router = useRouter();
  return (
    <section className="py-28 px-6 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] rounded-full opacity-60"
        style={{ background: "radial-gradient(ellipse, rgba(245,166,35,0.06) 0%, transparent 70%)" }} />

      <div className="relative max-w-lg mx-auto text-center">
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.6 }}>
          <span className="text-[var(--gold)] text-xs font-semibold tracking-[0.2em] uppercase">Your turn</span>
          <h2 className="font-display text-3xl md:text-4xl mt-2 mb-6">Get roasted. <em>Get a plan.</em></h2>
          <motion.button
            onClick={() => router.push("/roast")}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="px-10 py-4 bg-[var(--gold)] text-black font-bold text-base rounded-xl hover:bg-[var(--gold-dim)] transition-colors glow-gold"
          >
            Talk to Donald
          </motion.button>
        </motion.div>
      </div>
    </section>
  );
}
