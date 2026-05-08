/**
 * ElevenLabs **Client** tools for the voice UI (`DonaldConversation`).
 *
 * Privacy: the server **does not** merge voice-extracted fields into `session.profile`.
 * The agent passes a full **`profile`** object into `research_degree`; Firecrawl + Claude run on that
 * payload; the report card holds a one-off snapshot for `/report/{sessionId}` (in-memory until process ends).
 *
 * LinkedIn / manual form flows still use `POST /api/session` with a profile and may use other routes.
 *
 * ElevenLabs **system prompt** (personality + flow): `frontend/prompts/elevenlabs-donald-system.md`
 */

export const VOICE_AGENT_TOOL_NAMES = ["research_degree", "save_roast_quote"] as const;

export type VoiceAgentToolName = (typeof VOICE_AGENT_TOOL_NAMES)[number];

/** Tools the web app implements via `useConversation({ clientTools })`. */
export const VOICE_CLIENT_TOOL_NAME_SET = new Set<string>(VOICE_AGENT_TOOL_NAMES);

/** ElevenLabs `agent_tool_request` for these names usually means tools are Webhook/Server, not Client. */
export function isVoiceClientToolName(name: string): boolean {
  return VOICE_CLIENT_TOOL_NAME_SET.has(name);
}

/** Shape inside `research_degree` → POST body `profile` (snake_case or camelCase aliases). */
export type ResearchDegreeProfileParams = {
  name?: string;
  degree?: string;
  university?: string;
  graduation_year?: number;
  graduationYear?: number;
  current_job?: string;
  currentJob?: string;
  current_company?: string;
  currentCompany?: string;
  salary?: number | null;
  years_experience?: number | null;
  yearsExperience?: number | null;
  /** e.g. United Kingdom, UK, Germany */
  country_or_region?: string;
  countryOrRegion?: string;
  /** ISO 4217: GBP, USD, EUR — agent sets from user (e.g. £60k in London → GBP) */
  currency_code?: string;
  currencyCode?: string;
  /** Total degree tuition/fees the user says they paid or will pay (major units of currency_code). Canonical for the report when set. */
  tuition_paid?: number | null;
  tuitionPaid?: number | null;
  /** If false, tuition_paid is annual — backend approximates total (3yr UK-ish, 4yr otherwise). Default true. */
  tuition_is_total?: boolean;
  tuitionIsTotal?: boolean;
  source?: string;
};

export type SaveRoastQuoteToolParams = {
  quote: string;
};

/**
 * Markdown for ElevenLabs system prompt / tool descriptions.
 */
export const VOICE_AGENT_TOOLS_SPEC_MARKDOWN = `
## Client tools (exact names)

### \`research_degree\`
- **Purpose:** Run web research (Firecrawl) + structured analysis (Claude) from an **inline profile** — nothing is read from a stored user record for voice.
- **Parameters:** Provide a \`profile\` object (or pass fields at the top level; arrays \`profiles: [{...}]\` are supported — first entry is used).
- **profile fields (all optional in schema, but send what the user gave you):**
  - \`name\` (string)
  - \`degree\` (string)
  - \`university\` (string)
  - \`graduation_year\` (integer) — alias \`graduationYear\`
  - \`current_job\` (string) — alias \`currentJob\`
  - \`current_company\` (string) — alias \`currentCompany\`
  - \`salary\` (integer, optional)
  - \`years_experience\` (integer, optional) — alias \`yearsExperience\`
  - \`country_or_region\` (string, optional) — where they work/live (e.g. UK, Germany); alias \`countryOrRegion\`
  - \`currency_code\` (string, optional) — ISO 4217: **GBP**, **USD**, **EUR**, etc. Must match how they stated salary/tuition (e.g. £60k → GBP); alias \`currencyCode\`
  - \`tuition_paid\` (integer, optional) — total tuition they paid or are paying for the degree (major units); alias \`tuitionPaid\`. Strongly preferred for a concrete tuition line on the card; web search still runs for salaries and context.
  - \`tuition_is_total\` (boolean, optional, default true) — if false, \`tuition_paid\` is **annual** and the backend scales to an approximate total; alias \`tuitionIsTotal\`
  - \`source\` (string, optional; default voice)
- **Returns:** JSON with grades, \`honest_take\`, \`safeguard_tips\` (ordered top moves for post-roast survival segment), salary/tuition/AI risk fields, etc.
- **After tools:** When research_degree returns success (\`research_complete\` true), Phase 3 roast immediately — do not ask the user to confirm research. Phase 4: explain each safeguard tip as a move (what to do + brief why for this user); close with “if you only do one thing…”. Then \`save_roast_quote\` (roast one-liner only) and follow-ups. On failure, apologize and retry or clarify.

### \`save_roast_quote\`
- **Parameters:** \`quote\` (string, required)
- **Returns:** \`{ saved: true }\`
`.trim();
