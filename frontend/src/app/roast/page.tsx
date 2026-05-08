"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ConversationBubble from "@/components/ConversationBubble";
import DonaldConversation from "@/components/DonaldConversation";
import VoiceActivityPanel, { type VoiceActivityRow } from "@/components/VoiceActivityPanel";
import CVCoachSection from "@/components/CVCoachSection";
import Navbar from "@/components/Navbar";
import { createVoiceSession, fetchVoiceActivity, type CVAnalysisResult } from "@/lib/api";
import { BurningCapIcon, MicIcon } from "@/components/icons";

const ELEVENLABS_AGENT_CONFIGURED = !!process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;

function GlobeIcon({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={className}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

export default function RoastPage() {
  const router = useRouter();
  const [step, setStep] = useState<"choose" | "webcall">("choose");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [startError, setStartError] = useState<string>("");
  const [autoStartVoice, setAutoStartVoice] = useState(false);
  const [cvAnalysis, setCvAnalysis] = useState<CVAnalysisResult | null>(null);
  const [liveActivity, setLiveActivity] = useState<VoiceActivityRow[]>([]);
  const [serverActivity, setServerActivity] = useState<VoiceActivityRow[]>([]);
  const [activityPoll, setActivityPoll] = useState<{ ok: boolean; error?: string; at: number }>({
    ok: true,
    at: 0,
  });

  useEffect(() => {
    setLiveActivity([]);
    setServerActivity([]);
    setActivityPoll({ ok: true, at: 0 });
  }, [sessionId]);

  const appendLiveActivity = useCallback((row: VoiceActivityRow) => {
    setLiveActivity((prev) => [...prev, row]);
  }, []);

  useEffect(() => {
    if (!sessionId || step !== "webcall" || !ELEVENLABS_AGENT_CONFIGURED) return;
    let cancelled = false;
    const poll = async () => {
      const result = await fetchVoiceActivity(sessionId);
      if (cancelled) return;
      setActivityPoll({
        ok: result.ok,
        error: result.error,
        at: Date.now(),
      });
      if (result.ok) {
        setServerActivity(
          result.items.map((i) => ({
            id: `srv-${i.id}`,
            ts: new Date(i.ts).getTime(),
            source: "server" as const,
            event: i.event,
            title: i.title,
            detail: i.detail || undefined,
            data: i.data,
          }))
        );
      } else {
        setServerActivity([]);
      }
    };
    poll();
    const id = setInterval(poll, 1200);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [sessionId, step]);

  const mergedActivity = useMemo(
    () => [...liveActivity, ...serverActivity].sort((a, b) => a.ts - b.ts),
    [liveActivity, serverActivity]
  );

  const createAndStart = useCallback(async (opts?: { autoStart?: boolean }) => {
    setLoading(true);
    setStartError("");
    try {
      const session = await createVoiceSession();
      setSessionId(session.session_id);
      setAutoStartVoice(Boolean(opts?.autoStart));
      setStep("webcall");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not start voice call.";
      setStartError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <main className="relative min-h-screen flex flex-col overflow-x-hidden">
      <Navbar />
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse at center 30%, rgba(245,166,35,0.03) 0%, transparent 50%)" }} />

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-24 relative z-10">
        <AnimatePresence mode="wait">

          {/* ===== STEP 1: Choose how to talk to Donald ===== */}
          {step === "choose" && (
            <motion.div key="choose" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4 }} className="w-full max-w-lg mx-auto text-center">

              <BurningCapIcon size={40} className="text-[var(--gold)] mx-auto mb-6" />
              <h1 className="font-display text-3xl md:text-4xl mb-2">How do you want to <em>talk to Donald?</em></h1>
              <p className="text-[var(--subtle)] text-sm font-light mb-10 max-w-md mx-auto leading-relaxed">
                he&apos;ll roast your degree, coach your CV, and help you career max. web call only for now.
              </p>

              <div className="mb-8">
                <motion.button
                  onClick={() => {
                    void createAndStart();
                  }}
                  disabled={loading}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.98 }}
                  className="group p-6 rounded-2xl bg-[var(--card)] border border-white/8 hover:border-[var(--gold)]/30 text-left transition-all disabled:opacity-50 max-w-sm mx-auto"
                >
                  <div className="w-12 h-12 rounded-xl bg-[var(--gold)]/10 border border-[var(--gold)]/20 flex items-center justify-center mb-4 group-hover:bg-[var(--gold)]/15 transition-colors">
                    <GlobeIcon size={22} className="text-[var(--gold)]" />
                  </div>
                  <h3 className="text-base font-semibold mb-1">Web Call</h3>
                  <p className="text-[var(--subtle)] text-xs font-light leading-relaxed">
                    talk to Donald right here in your browser. no download, no signup. roast + real career advice.
                  </p>
                  <div className="mt-4 flex items-center gap-1.5 text-[var(--gold)] text-xs font-semibold">
                    <MicIcon size={14} />
                    start now
                  </div>
                </motion.button>
              </div>
              {startError && (
                <p className="text-red-300 text-xs mt-3 max-w-md mx-auto">
                  {startError}
                </p>
              )}

              <p className="text-[var(--subtle)]/30 text-[10px] mt-6">
                we don&apos;t store anything. Donald forgets you the second the call ends.
              </p>
            </motion.div>
          )}

          {/* ===== STEP 2b: Web call active ===== */}
          {step === "webcall" && (
            <motion.div
              key="webcall"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
              className={`w-full mx-auto ${ELEVENLABS_AGENT_CONFIGURED ? "max-w-5xl" : "max-w-lg"} text-center`}
            >
              <h1 className="font-display text-3xl md:text-4xl mb-2">The Call Is <em>Live</em></h1>
              {ELEVENLABS_AGENT_CONFIGURED ? (
                <p className="text-[var(--subtle)] text-sm font-light mb-6 max-w-xl mx-auto">
                  The panel on the right shows what you said and the facts Donald’s pulling — you’ll see a progress bar while he’s digging.
                </p>
              ) : (
                <p className="text-[var(--subtle)] text-sm font-light mb-4">
                  Donald is in the bubble. bottom right corner. go talk to him bestie.
                </p>
              )}
              {ELEVENLABS_AGENT_CONFIGURED && sessionId ? (
                <div className="grid lg:grid-cols-2 gap-6 items-start text-left w-full">
                  <div className="flex flex-col items-center lg:items-center mx-auto w-full max-w-md">
                    <DonaldConversation
                      sessionId={sessionId}
                      onComplete={() => router.push(`/report/${sessionId}`)}
                      onSdkActivity={appendLiveActivity}
                      autoStart={autoStartVoice}
                      onCvAnalysis={setCvAnalysis}
                    />
                  </div>
                  <VoiceActivityPanel
                    items={mergedActivity}
                    pollOk={activityPoll.ok}
                    pollError={activityPoll.error}
                    pollAt={activityPoll.at}
                  />
                </div>
              ) : null}
              {cvAnalysis && (
                <CVCoachSection analysis={cvAnalysis} />
              )}
              {!ELEVENLABS_AGENT_CONFIGURED && (
                <div className="flex items-center justify-center gap-2 text-[var(--gold)] text-xs">
                  <span className="w-2 h-2 rounded-full bg-[var(--gold)] animate-pulse" />
                  voice call active (demo)
                </div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* Demo-only bubble when no ElevenLabs agent id */}
      {step === "webcall" && sessionId && !ELEVENLABS_AGENT_CONFIGURED && (
        <ConversationBubble sessionId={sessionId} onComplete={() => router.push(`/report/${sessionId}`)} />
      )}
    </main>
  );
}
