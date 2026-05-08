"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { createSession } from "@/lib/api";

export default function LandingForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"choice" | "manual">("choice");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "", degree: "", university: "",
    graduation_year: new Date().getFullYear(),
    current_job: "", current_company: "",
    salary: undefined as number | undefined,
    years_experience: undefined as number | undefined,
  });

  const handleManual = async () => {
    setLoading(true);
    try {
      const session = await createSession({
        ...form,
        years_experience: form.years_experience,
        source: "manual",
      });
      router.push(`/roast?session=${session.session_id}`);
    } catch {
      setError("Server\u2019s not responding. Very unfair.");
    }
    setLoading(false);
  };

  const input = "w-full px-4 py-3 bg-[var(--card)] border border-white/10 rounded-xl text-[var(--fg)] text-sm placeholder:text-[var(--subtle)] focus:outline-none focus:border-[var(--gold)]/40 focus:ring-1 focus:ring-[var(--gold)]/20 transition-all";

  return (
    <div className="w-full max-w-sm mx-auto" id="talk-donald">
      <AnimatePresence mode="wait">
        {mode === "choice" && (
          <motion.div key="choice" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.3 }} className="flex flex-col gap-3">
            <motion.button onClick={() => setMode("manual")} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              className="w-full py-3.5 bg-[var(--card)] border border-white/10 font-semibold text-sm rounded-xl hover:bg-[var(--card-hover)] hover:border-white/20 transition-all">
              I&apos;ll Enter My Info
            </motion.button>
            <p className="text-center text-[var(--subtle)] text-xs mt-1">We don&apos;t store your data. Donald has bigger things to remember.</p>
          </motion.div>
        )}

        {mode === "manual" && (
          <motion.div key="manual" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.3 }} className="flex flex-col gap-2.5">
            {error && <p className="text-[var(--red)] text-xs font-display italic">&ldquo;{error}&rdquo;</p>}
            <input placeholder="Your name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={input} autoFocus />
            <input placeholder="Degree (e.g. Communications, Finance)" value={form.degree} onChange={(e) => setForm({ ...form, degree: e.target.value })} className={input} />
            <input placeholder="University" value={form.university} onChange={(e) => setForm({ ...form, university: e.target.value })} className={input} />
            <div className="grid grid-cols-2 gap-2.5">
              <input type="number" placeholder="Grad year" value={form.graduation_year || ""} onChange={(e) => setForm({ ...form, graduation_year: parseInt(e.target.value) || 0 })} className={input} />
              <input type="number" placeholder="Salary (optional)" value={form.salary || ""} onChange={(e) => setForm({ ...form, salary: e.target.value ? parseInt(e.target.value) : undefined })} className={input} />
            </div>
            <input placeholder="Current job title" value={form.current_job} onChange={(e) => setForm({ ...form, current_job: e.target.value })} className={input} />
            <input type="number" min={0} max={60} placeholder="Years in role / field (optional, helps AI risk)" value={form.years_experience ?? ""} onChange={(e) => setForm({ ...form, years_experience: e.target.value ? parseInt(e.target.value, 10) : undefined })} className={input} />
            <button onClick={handleManual} disabled={loading || !form.name || !form.degree || !form.university}
              className="w-full py-3.5 bg-[var(--gold)] text-black font-semibold text-sm rounded-xl hover:bg-[var(--gold-dim)] transition-colors glow-gold disabled:opacity-40 mt-1">
              {loading ? "Setting up your session..." : "Run my vibe check"}
            </button>
            <button onClick={() => { setMode("choice"); setError(""); }} className="text-[var(--subtle)] text-xs hover:text-[var(--fg)] transition-colors">Back</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
