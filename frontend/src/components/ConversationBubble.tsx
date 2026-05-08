"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MicIcon, DonaldLogo } from "./icons";
import { getDegreeTier } from "@/lib/degreeTier";

const DEMO_MODE = !process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;

interface Props {
  sessionId: string;
  onComplete: () => void;
}

const RESEARCH_STATUSES = [
  { text: "researching your salary...", icon: "💰" },
  { text: "pulling up tuition data...", icon: "🎓" },
  { text: "checking AI replacement risk...", icon: "🤖" },
  { text: "searching reddit opinions...", icon: "💀" },
  { text: "calculating what you could\u2019ve invested...", icon: "📈" },
  { text: "locking in the honest take...", icon: "🎯" },
  { text: "oh this is gonna hurt...", icon: "😬" },
];

const REAL_TALK_LINES = [
  { text: "\"you paid HOW much for that degree?\"", icon: "💸" },
  { text: "\"the S&P 500 is crying rn\"", icon: "📉" },
  { text: "\"ChatGPT does your job for $20/month\"", icon: "🤖" },
  { text: "\"your parents are NOT okay\"", icon: "😭" },
  { text: "\"this degree is absolutely cooked\"", icon: "🔥" },
];

type Phase = "idle" | "connecting" | "chatting" | "researching" | "delivering" | "verdict" | "done";

export default function ConversationBubble({ sessionId, onComplete }: Props) {
  const [open, setOpen] = useState(true);
  const [phase, setPhase] = useState<Phase>("idle");
  const [statusText, setStatusText] = useState("tap to talk to Donald");
  const [statusIcon, setStatusIcon] = useState("🎙️");
  const [mockSpeaking, setMockSpeaking] = useState(false);
  const [shaking, setShaking] = useState(false);
  const [fireRain, setFireRain] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // For real mode
  const conversationRef = useRef<any>(null);
  const [realSpeaking, setRealSpeaking] = useState(false);

  const isSpeaking = DEMO_MODE ? mockSpeaking : realSpeaking;

  // Cleanup
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // ── Demo mode: simulate the full conversation flow ──
  const startDemo = useCallback(() => {
    setPhase("connecting");
    setStatusText("connecting to Donald...");
    setStatusIcon("📡");

    // Phase 1: Connected → chatting
    timerRef.current = setTimeout(() => {
      setPhase("chatting");
      setMockSpeaking(true);
      setStatusText("Donald is introducing himself...");
      setStatusIcon("🔥");

      // Donald talks for 3s
      timerRef.current = setTimeout(() => {
        setMockSpeaking(false);
        setStatusText("your turn. tell Donald about your degree.");
        setStatusIcon("🎙️");

        // User "talks" for 3s
        timerRef.current = setTimeout(() => {
          setMockSpeaking(true);
          setStatusText("Donald is asking follow-up questions...");
          setStatusIcon("🤔");

          // Donald responds
          timerRef.current = setTimeout(() => {
            setMockSpeaking(false);
            setStatusText("your turn. speak now.");
            setStatusIcon("🎙️");

            // Transition to research phase
            timerRef.current = setTimeout(() => {
              setPhase("researching");
              setMockSpeaking(false);
              setStatusText("hold on... pulling up the receipts...");
              setStatusIcon("🔍");

              // Cycle through research statuses
              let idx = 0;
              intervalRef.current = setInterval(() => {
                if (idx < RESEARCH_STATUSES.length) {
                  setStatusText(RESEARCH_STATUSES[idx].text);
                  setStatusIcon(RESEARCH_STATUSES[idx].icon);
                  idx++;
                } else {
                  if (intervalRef.current) clearInterval(intervalRef.current);
                  // Transition to voice reality check
                  setPhase("delivering");
                  setMockSpeaking(true);
                  setStatusText("Donald is going off (respectfully)...");
                  setStatusIcon("🔥");

                  // Shake effect
                  setTimeout(() => {
                    setShaking(true);
                    setTimeout(() => setShaking(false), 500);
                  }, 500);

                  // Cycle real-talk lines
                  let lineIdx = 0;
                  intervalRef.current = setInterval(() => {
                    if (lineIdx < REAL_TALK_LINES.length) {
                      setStatusText(REAL_TALK_LINES[lineIdx].text);
                      setStatusIcon(REAL_TALK_LINES[lineIdx].icon);
                      // Shake on each line
                      setShaking(true);
                      setTimeout(() => setShaking(false), 400);
                      lineIdx++;
                    } else {
                      if (intervalRef.current) clearInterval(intervalRef.current);
                      // Fire rain!
                      setFireRain(true);
                      setTimeout(() => setFireRain(false), 3000);

                      // Verdict
                      setPhase("verdict");
                      setMockSpeaking(true);
                      setStatusText(`"${getDegreeTier("D").badge}" — that's the vibe.`);
                      setStatusIcon("⚖️");

                      setTimeout(() => {
                        setMockSpeaking(false);
                        setPhase("done");
                        setStatusText("the verdict has been delivered.");
                        setStatusIcon("💀");
                        setTimeout(onComplete, 2500);
                      }, 3000);
                    }
                  }, 2000);
                }
              }, 2000);

            }, 2000);
          }, 3000);
        }, 3000);
      }, 3000);
    }, 1500);
  }, [onComplete]);

  // ── Real mode: use ElevenLabs ──
  const startReal = useCallback(async () => {
    setPhase("connecting");
    setStatusText("connecting to Donald...");
    setStatusIcon("📡");
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      const { useConversation } = await import("@elevenlabs/react");
      // Note: in real mode this would use the hook properly
      // For now this is a placeholder — the real implementation
      // uses the hook at component level
    } catch {
      setStatusText("mic access required fr.");
      setStatusIcon("🚫");
      setPhase("idle");
    }
  }, [sessionId]);

  const start = DEMO_MODE ? startDemo : startReal;

  const end = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setMockSpeaking(false);
    setPhase("done");
    setStatusText("call ended.");
    setStatusIcon("📵");
    setTimeout(onComplete, 2000);
  }, [onComplete]);

  return (
    <>
      {/* Fire rain overlay */}
      <AnimatePresence>
        {fireRain && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 pointer-events-none z-[60] overflow-hidden"
          >
            {Array.from({ length: 24 }).map((_, i) => (
              <motion.span
                key={i}
                initial={{ y: -40, opacity: 1 }}
                animate={{ y: "110vh", opacity: 0 }}
                transition={{ duration: 1.5 + Math.random(), delay: Math.random() * 1, ease: "easeIn" as const }}
                className="absolute text-xl select-none"
                style={{ left: `${3 + (i * 4.1) % 94}%` }}
              >
                {["🔥", "💀", "😭", "📉", "🤡", "💸"][i % 6]}
              </motion.span>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className={`fixed bottom-6 right-6 z-50 w-[340px] bg-[var(--card)] border border-white/10 rounded-3xl shadow-2xl shadow-black/40 overflow-hidden ${
              shaking ? "animate-[shake_0.5s_ease-in-out]" : ""
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
              <div className="flex items-center gap-2.5">
                <div className={`w-2 h-2 rounded-full transition-colors ${
                  phase === "idle" || phase === "done" ? "bg-[var(--subtle)]" : "bg-[var(--gold)] animate-pulse"
                }`} />
                <span className="font-display text-sm">Donald</span>
                <span className="text-[var(--subtle)] text-[10px] uppercase tracking-wider">
                  {phase === "idle" ? "ready" : phase === "done" ? "ended" : "live"}
                </span>
              </div>
              <button
                onClick={() => { if (phase !== "idle" && phase !== "done") end(); else setOpen(false); }}
                className="text-[var(--subtle)] hover:text-[var(--fg)] text-xs transition-colors"
              >
                {phase === "idle" || phase === "done" ? "close" : "end call"}
              </button>
            </div>

            {/* Main content */}
            <div className="px-5 py-8 flex flex-col items-center gap-5 min-h-[260px] justify-center">

              {/* Animated orb */}
              <div className="relative">
                <motion.div
                  animate={isSpeaking ? { scale: [1, 1.08, 1] } : { scale: 1 }}
                  transition={isSpeaking ? { duration: 0.8, repeat: Infinity, ease: "easeInOut" as const } : { duration: 0.3 }}
                  className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500 ${
                    phase === "idle"
                      ? "bg-[var(--bg)] border border-white/10"
                      : isSpeaking
                      ? "bg-[var(--gold)]/15 border-2 border-[var(--gold)] shadow-[0_0_40px_rgba(245,166,35,0.2)]"
                      : phase === "done"
                      ? "bg-[var(--bg)] border border-white/10"
                      : "bg-[var(--bg)] border-2 border-[var(--gold)]/30"
                  }`}
                >
                  <DonaldLogo className={`scale-[1.5] transition-colors duration-500 ${
                    isSpeaking ? "text-[var(--gold)]" : phase === "delivering" || phase === "verdict" ? "text-[var(--red)]" : "text-[var(--fg)]"
                  }`} />
                </motion.div>

                {/* Outer ring when speaking */}
                {isSpeaking && (
                  <motion.div
                    className="absolute inset-[-8px] rounded-full border border-[var(--gold)]/30"
                    animate={{ scale: [1, 1.2, 1], opacity: [0.4, 0, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" as const }}
                  />
                )}
              </div>

              {/* Audio bars */}
              <div className="flex items-end gap-[3px] h-5">
                {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                  <motion.div
                    key={i}
                    className="w-[3px] rounded-full"
                    animate={{
                      height: isSpeaking ? [6, 10 + ((i * 7) % 12), 6] : [2, 2, 2],
                      opacity: isSpeaking ? [0.4, 0.8, 0.4] : [0.1, 0.1, 0.1],
                      backgroundColor: isSpeaking
                        ? phase === "delivering" || phase === "verdict" ? "var(--red)" : "var(--gold)"
                        : "var(--subtle)",
                    }}
                    transition={isSpeaking ? {
                      duration: 0.4 + (i * 0.05),
                      repeat: Infinity,
                      repeatType: "reverse" as const,
                      delay: i * 0.06,
                    } : { duration: 0.3 }}
                  />
                ))}
              </div>

              {/* Status */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={statusText}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center gap-2 text-center max-w-[280px]"
                >
                  <span className="text-base shrink-0">{statusIcon}</span>
                  <span className={`text-xs font-light ${
                    phase === "delivering" || phase === "verdict" ? "text-[var(--fg)] font-display italic" : "text-[var(--subtle)]"
                  }`}>{statusText}</span>
                </motion.div>
              </AnimatePresence>

              {/* Action buttons */}
              {phase === "idle" && (
                <motion.button
                  onClick={start}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  className="px-7 py-3 bg-[var(--gold)] text-black font-bold text-sm rounded-xl hover:bg-[var(--gold-dim)] transition-colors glow-gold flex items-center gap-2"
                >
                  <MicIcon size={16} />
                  Talk to Donald
                </motion.button>
              )}

              {phase === "connecting" && (
                <div className="flex items-center gap-2 text-[var(--subtle)] text-xs">
                  <span className="w-4 h-4 border-2 border-[var(--gold)]/30 border-t-[var(--gold)] rounded-full animate-spin" />
                  connecting...
                </div>
              )}

              {(phase === "chatting" || phase === "researching" || phase === "delivering" || phase === "verdict") && (
                <button onClick={end}
                  className="px-5 py-2 bg-[var(--bg)] border border-white/10 rounded-lg text-xs text-[var(--subtle)] hover:text-[var(--fg)] hover:border-white/20 transition-all">
                  End Call
                </button>
              )}

              {phase === "done" && (
                <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
                  <p className="text-[var(--gold)] text-xs font-display italic mb-3">loading your vibe sheet...</p>
                  <div className="w-5 h-5 mx-auto border-2 border-[var(--gold)]/30 border-t-[var(--gold)] rounded-full animate-spin" />
                </motion.div>
              )}
            </div>

            {/* Bottom tip */}
            {phase !== "idle" && phase !== "done" && (
              <div className="px-5 py-2 border-t border-white/5 bg-[var(--bg)]/50">
                <p className="text-[var(--subtle)]/50 text-[10px] text-center">
                  {phase === "researching" ? "Donald is doing his homework. this takes a sec."
                    : phase === "delivering" || phase === "verdict" ? "oh no. oh no no no."
                    : isSpeaking ? "Donald is talking. interrupting is rude but go off."
                    : "speak clearly. Donald judges mumbling too."}
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed bubble */}
      <AnimatePresence>
        {!open && phase !== "done" && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            onClick={() => setOpen(true)}
            className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[var(--gold)] text-black flex items-center justify-center shadow-lg shadow-[var(--gold)]/20 hover:scale-110 active:scale-95 transition-transform"
          >
            <DonaldLogo className="scale-110 text-black" />
          </motion.button>
        )}
      </AnimatePresence>
    </>
  );
}
