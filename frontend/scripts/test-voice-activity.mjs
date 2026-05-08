/**
 * Smoke test: session → GET voice-activity (no profile stored for voice).
 * Run from frontend/: node scripts/test-voice-activity.mjs
 */
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function main() {
  const s = await fetch(`${API}/api/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "",
      degree: "",
      university: "",
      graduation_year: 0,
      current_job: "",
      source: "voice",
    }),
  });
  if (!s.ok) throw new Error(`POST /api/session ${s.status} ${await s.text()}`);
  const { session_id } = await s.json();
  console.log("session_id:", session_id);

  const a = await fetch(`${API}/api/session/${session_id}/voice-activity`, { cache: "no-store" });
  const j = await a.json();
  console.log("voice-activity:", a.status, "items:", (j.items || []).length);
  console.log(JSON.stringify(j.items, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
