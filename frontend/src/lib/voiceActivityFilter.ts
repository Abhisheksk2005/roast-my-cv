/** Minimal shape for filtering (avoids circular import with VoiceActivityPanel). */
export type ActivityRowFilterInput = {
  event: string;
  title: string;
};

/** Events shown in the Activity sidebar: your speech, research pipeline, tool calls, and CV coaching. */
const IMPORTANT_EVENTS = new Set([
  "transcript",
  "webrtc_ready",
  "client_tool",
  "client_tool_error",
  "client_tool_unhandled",
  "webhook_research_started",
  "webhook_research_complete",
  "webhook_save_roast_quote",
  "cv_upload",
  "cv_ready",
  "cv_error",
  "error",
  "disconnect",
]);

export function isImportantActivityRow(row: ActivityRowFilterInput): boolean {
  if (!IMPORTANT_EVENTS.has(row.event)) return false;
  if (row.event === "transcript" && row.title !== "You said") return false;
  return true;
}

export function filterActivityForFeed<T extends ActivityRowFilterInput>(items: T[]): T[] {
  return items.filter(isImportantActivityRow);
}
