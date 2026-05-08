# Donald backend — setup

## Architecture

```
User profile
     │
     ▼
┌─────────────────────────────────────────┐
│  Firecrawl (parallel web search)        │  ← FIRECRAWL_API_KEY
│  9 queries: salary, tuition, ROI,       │
│  S&P 500, job trend, AI risk, reddit    │
└───────────────┬─────────────────────────┘
                │ raw snippets
                ▼
┌─────────────────────────────────────────┐
│  Claude (Haiku — see ANTHROPIC_ANALYSIS_MODEL) │  ← ANTHROPIC_API_KEY
│  Single structured tool_use call:       │
│  • Extract salary, tuition, S&P return  │
│  • AI replacement risk (0–100) + why    │
│  • Job market trend                     │
│  • Personalized safeguard tips          │
│  • Honest take (report card copy)       │
└───────────────┬─────────────────────────┘
                │ LLMAnalysis
                ▼
┌─────────────────────────────────────────┐
│  Derived fields + grading               │
│  • tuition_if_invested (compound math)  │
│  • tuition_opportunity_gap              │
│  • overall_cooked_0_100 (blend)         │
│  • Letter grade A–F                     │
└─────────────────────────────────────────┘
```

**Fallback chain:** If `ANTHROPIC_API_KEY` is missing or Claude fails → regex extraction + rule-based heuristics from `ai_job_model.py`. If `FIRECRAWL_API_KEY` is also missing → job-title-only heuristics (no financial data).

**Firecrawl SDK:** Use `firecrawl-py` **4.x** (see `requirements.txt`). Version **1.x** exposed `search()` but it always raised `NotImplementedError`, so every query returned empty — research looked “broken” even with a valid API key.

## Environment variables

| Variable | Required | Purpose | Where |
|----------|----------|---------|-------|
| `FIRECRAWL_API_KEY` | Recommended | Web search (salary, tuition, AI risk snippets) | [firecrawl.dev](https://firecrawl.dev) |
| `ANTHROPIC_API_KEY` | Recommended | Claude structured extraction + tips + honest take | [console.anthropic.com](https://console.anthropic.com) |
| `ANTHROPIC_ANALYSIS_MODEL` | No | Default `claude-haiku-4-5`. Set a dated id if your org requires it (e.g. `claude-haiku-4-5-20251001`). Avoid retired ids like `claude-3-5-haiku-latest`. |
| `FRONTEND_URL` | No | CORS origin for production deploy | Your Vercel/etc URL |

Copy `.env.example` → `.env` in this folder and fill in values.

## Frontend env

In `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your-agent-id
```

## Voice-first flow (ElevenLabs)

1. **Create a session** before starting the voice client: `POST /api/session` with an empty placeholder profile. Put `session_id` in the agent’s **dynamic variables**. The server **does not** accumulate voice answers into `session.profile`.
2. When ready, the agent calls **`POST /api/webhooks/research_degree`** with JSON `{ "session_id": "…", "profile": { "degree": "…", "university": "…", "graduation_year": 2020, "current_job": "…", … } }` — everything the model extracted in one object (snake_case or camelCase). That runs Firecrawl + Claude and writes the **report card** (snapshot only; not merged into the session profile).
3. Optional: **`save_roast_quote`** with `{ "session_id", "quote" }` after research.
4. LinkedIn / form flows may still use **`update_user_profile`** / stored profiles; voice uses inline `profile` on `research_degree` only.

If the voice session **drops immediately** with a console error about `error_type`, the server often sent a malformed `error` event (commonly **`missing_dynamic_variable`**). Fix the **`session_id`** dynamic variable JSON path (try `dynamic_variables.session_id` or `session_id`) in the ElevenLabs UI. The frontend applies a small **patch** to `@elevenlabs/client` (via `patch-package` on `npm install`) so this does not crash React.

**Local dev without ngrok:** ElevenLabs **cannot** call `http://127.0.0.1` from their cloud. The Donald frontend registers **client tools** `research_degree` and `save_roast_quote` in `@elevenlabs/react` that POST from the **user’s browser**. Tool parameter reference: `frontend/src/lib/voiceAgentTools.ts`. For production you can use **webhook** tools with a public API URL instead.

### Accessing the agent from the browser (auth)

Per [@elevenlabs/react](https://www.npmjs.com/package/@elevenlabs/react):

- **Public agent** (no client auth): set `NEXT_PUBLIC_ELEVENLABS_AGENT_ID` and keep `NEXT_PUBLIC_ELEVENLABS_USE_TOKEN=false`. The SDK connects with `agentId` only.
- **Private / auth-required agent**: set `ELEVENLABS_API_KEY` in **`backend/.env`** (never in the frontend), set `NEXT_PUBLIC_ELEVENLABS_USE_TOKEN=true`, and restart both servers. The UI calls `GET /api/convai/conversation-token?agent_id=...` on your API; the API mints a short-lived WebRTC token from ElevenLabs.
- **Token minting restriction (recommended):** set `ELEVENLABS_ALLOWED_AGENT_IDS` (comma-separated) or `ELEVENLABS_AGENT_ID` (single id). If set, the backend returns `403` for any other `agent_id`.

Optional: if you test a **draft branch**, set `NEXT_PUBLIC_ELEVENLABS_BRANCH_ID` to the `branchId` from the ElevenLabs URL and the same query is forwarded when minting the token.

## Run locally

```bash
cd path/to/donald/donald
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: `http://127.0.0.1:8000/docs`

## Key routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/session` | POST | Create session (profile + optional `years_experience`) |
| `/api/session/{id}/voice-activity` | GET | Poll during voice: webhook + research steps for activity UI |
| `/api/research` | POST | Queue research (Celery) → `202` + `task_id`, or sync if `CELERY_DISABLED=1` |
| `/api/research/task/{task_id}/status` | GET | Celery task status |
| `/api/research/task/{task_id}/result` | GET | Fetch result + persist to session |
| `/health` | GET | Liveness |
| `/ready` | GET | Redis + Firestore readiness |
| `/api/report-card/{id}` | GET | Fetch report (grade, financials, AI risk, tips, honest take) |
| `/api/webhooks/update_user_profile` | POST | Merge profile fields from conversation (partial JSON) |
| `/api/webhooks/research_degree` | POST | Same as research, webhook format for voice agent |
| `/api/webhooks/save_roast_quote` | POST | Save ElevenLabs voice quote to report |
| `/api/convai/conversation-token` | GET | WebRTC token proxy (`agent_id` query; needs `ELEVENLABS_API_KEY` when using token mode) |

## Cost per session

| Service | ~Cost |
|---------|-------|
| Firecrawl | 9 searches × ~$0.001 = ~$0.01 |
| Claude (haiku) | 1 call, ~1200 tokens out = ~$0.002 |
| **Total** | **~$0.012** |

## Firestore security rules

Repo root includes [`firestore.rules`](../firestore.rules): **deny all** reads/writes from client SDKs (your API uses the **Admin SDK** and ignores these rules).

Deploy to Firebase (requires [Firebase CLI](https://firebase.google.com/docs/cli)):

```bash
cd path/to/donald/donald
firebase login
firebase deploy --only firestore:rules
```

Project is set in [`.firebaserc`](../.firebaserc) (`heyitdonald`). You can also paste the same rules in **Firebase console → Firestore → Rules**.

**Important:** If your shell has `FIRESTORE_DISABLED=1` (e.g. from a test), the API will **not** use Firestore — unset it in production: `Remove-Item Env:FIRESTORE_DISABLED` (PowerShell) or `unset FIRESTORE_DISABLED` (bash).

## Production (Railway / Docker)

- **Firestore:** Set `GOOGLE_CLOUD_PROJECT` or `FIRESTORE_PROJECT_ID` and credentials (`GOOGLE_APPLICATION_CREDENTIALS` or workload identity). Use `FIRESTORE_DISABLED=1` only for local dev without GCP.
- **Redis:** Set `REDIS_URL` (Railway Redis plugin provides this). Use `REDIS_DISABLED=1` only when you intentionally skip Redis.
- **Celery:** Run a **worker** service: `celery -A backend.celery_app worker -l info`. Set `CELERY_DISABLED=1` on the API if you are not running Redis/workers (HTTP `POST /api/research` then runs **synchronously** in the API process).
- **Observability:** `SENTRY_DSN`, optional `OTEL_EXPORTER_OTLP_ENDPOINT` (HTTP OTLP; path `/v1/traces` is appended automatically).
- **Docker Compose:** From repo root `donald/`, `docker compose up --build` starts API + worker + Redis (see `docker-compose.yml`).
- **Health:** `GET /health` (liveness), `GET /ready` (Redis + Firestore checks when enabled).
