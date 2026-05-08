/** Live client tool rows — keep titles stable for progress detection */
export const VOICE_RESEARCH_CLIENT_START_TITLE = "Crunching your numbers";
export const VOICE_RESEARCH_CLIENT_DONE_TITLE = "Numbers are back";
export const VOICE_RESEARCH_CLIENT_ERROR_TITLE = "Research hit a snag";

type ProgressRow = { ts: number; event: string; title: string };

/**
 * True while a research run has started (client or server) and has not finished or failed yet.
 */
export function isVoiceResearchInProgress(rows: ProgressRow[]): boolean {
  let lastStart = 0;
  let lastEnd = 0;
  const sorted = [...rows].sort((a, b) => a.ts - b.ts);
  for (const r of sorted) {
    if (
      r.event === "webhook_research_started" ||
      (r.event === "client_tool" && r.title === VOICE_RESEARCH_CLIENT_START_TITLE)
    ) {
      lastStart = Math.max(lastStart, r.ts);
    }
    if (
      r.event === "webhook_research_complete" ||
      (r.event === "client_tool" && r.title === VOICE_RESEARCH_CLIENT_DONE_TITLE) ||
      (r.event === "client_tool_error" && r.title === VOICE_RESEARCH_CLIENT_ERROR_TITLE)
    ) {
      lastEnd = Math.max(lastEnd, r.ts);
    }
  }
  return lastStart > lastEnd;
}
