"use client";

import { motion } from "framer-motion";
import { BurningCapIcon, MoneyBurningIcon, CrackingDiplomaIcon, GavelIcon } from "./icons";

const features = [
  {
    icon: BurningCapIcon,
    title: "Voice roast + real talk",
    desc: "Live voice breakdown with real salary & tuition data. Then actual career advice.",
    color: "var(--red)",
  },
  {
    icon: MoneyBurningIcon,
    title: "AI risk + market facts",
    desc: "How fast AI is moving in your field and what the job market actually looks like.",
    color: "var(--gold)",
  },
  {
    icon: CrackingDiplomaIcon,
    title: "One-word verdict",
    desc: "Valid, Mid, Cooked — one label for your degree. Then moves to fix it.",
    color: "var(--red)",
  },
  {
    icon: GavelIcon,
    title: "Career max game plan",
    desc: "Concrete next moves to level up, not motivational fluff. Resume, outreach, skills.",
    color: "var(--gold)",
  },
];

export default function FeaturesSection() {
  return (
    <section className="py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.6 }} className="text-center mb-12">
          <span className="text-[var(--gold)] text-xs font-semibold tracking-[0.2em] uppercase">At a glance</span>
          <h2 className="font-display text-3xl md:text-4xl mt-2">Roast + <em>game plan</em></h2>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((f, i) => (
            <motion.div key={f.title} initial={{ opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.5, delay: i * 0.12 }}
              whileHover={{ y: -4 }}
              className="p-7 rounded-2xl bg-[var(--card)] border border-white/5 hover:border-white/10 transition-colors overflow-hidden">
              <div className="mb-5" style={{ color: f.color }}><f.icon size={36} /></div>
              <h3 className="text-base font-semibold mb-2">{f.title}</h3>
              <p className="text-[var(--subtle)] text-sm leading-relaxed font-light">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
