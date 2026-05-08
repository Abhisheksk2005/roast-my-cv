# ElevenLabs: why tools “don’t run” on heyitsdonald.com

This site runs **`research_degree`** and **`save_roast_quote` in the user’s browser** (`DonaldConversation` → `clientTools`).  
ElevenLabs must treat them as **Client** tools, not **Webhook** / **Server** tools.

## Quick checks

1. **Tool type = Client**  
   In ElevenLabs: **Conversational AI → your agent → Tools**  
   - `research_degree` → type **Client**  
   - `save_roast_quote` → type **Client**  
   If either is **Webhook** with a URL, the model may “call” the tool but **your API is never hit from this page** (and you won’t see “Pulling public salary…” in the activity panel).

2. **Exact names** (snake_case)  
   `research_degree` and `save_roast_quote` — must match what’s in code (`voiceAgentTools.ts`).

3. **No duplicates**  
   Remove extra tools with the same name or old `update_user_profile` webhooks if you’re not using them for voice.

4. **Import the JSON**  
   Use **`frontend/prompts/elevenlabs-client-tools.json`** as the source of truth for Client tool definitions (parameters, timeouts).

5. **Draft branch**  
   If you use `NEXT_PUBLIC_ELEVENLABS_BRANCH_ID`, that **branch** must also have the same Client tools as production.

6. **Activity panel hints**  
   - If you see **“Double-checking your story”** / client-tool titles → browser tools are working.  
   - If you only see generic **“One moment…”** and never client steps → often **webhook tools** instead of client tools.

7. **Model**  
   Use a Conversational AI model / agent config that **supports tool calling** (check ElevenLabs docs for your plan).

## System prompt

Copy from **`elevenlabs-donald-system.md`** (or compact variant). It tells the agent to call `research_degree` after Tier 1 fields.
