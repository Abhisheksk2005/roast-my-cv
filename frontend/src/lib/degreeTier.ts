/** Maps API letter grades (A–F) to Gen Z labels for AI / job risk (shown in the UI). */

export interface DegreeTier {
  badge: string;
  vibeLine: string;
  color: string;
}

const MID: DegreeTier = {
  badge: "Mid",
  vibeLine: "not doomed, not safe — half your tasks are already assistant energy.",
  color: "#facc15",
};

export function getDegreeTier(grade: string): DegreeTier {
  const g = (grade || "").toUpperCase().trim().charAt(0);
  switch (g) {
    case "A":
      return {
        badge: "Valid",
        vibeLine: "your lane still passes the vibe check. AI isn't eating the whole job yet.",
        color: "#4ade80",
      };
    case "B":
      return {
        badge: "Aight",
        vibeLine: "you're fine for now — just stay ahead of what models can do in your field.",
        color: "#60a5fa",
      };
    case "C":
      return MID;
    case "D":
      return {
        badge: "Cooked",
        vibeLine: "AI overlap is serious — your tasks are looking real automatable. time to pivot.",
        color: "#fb923c",
      };
    case "F":
      return {
        badge: "Pack it up buddy",
        vibeLine: "this career path is getting erased by automation. new plan, no debate.",
        color: "#ef4444",
      };
    default:
      return MID;
  }
}
