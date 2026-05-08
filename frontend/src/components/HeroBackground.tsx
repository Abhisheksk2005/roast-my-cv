"use client";

export default function HeroBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Gold orb top-right */}
      <div
        className="absolute -top-40 -right-40 w-[700px] h-[700px] rounded-full animate-drift opacity-60"
        style={{ background: "radial-gradient(circle, rgba(245,166,35,0.07) 0%, transparent 60%)" }}
      />
      {/* Red orb bottom-left */}
      <div
        className="absolute -bottom-32 -left-32 w-[500px] h-[500px] rounded-full animate-drift opacity-50"
        style={{ background: "radial-gradient(circle, rgba(230,57,70,0.05) 0%, transparent 60%)", animationDirection: "reverse" }}
      />
      {/* Subtle grid */}
      <div
        className="absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }}
      />
    </div>
  );
}
