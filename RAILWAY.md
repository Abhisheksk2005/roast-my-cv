# Deploy backend on Railway

## 1. Repo

Push your code to **GitHub** (or GitLab). Ensure the repo root contains `backend/`, `requirements.txt` (root file installs `backend/requirements.txt`), and `railway.toml`.

## 2. Create project

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Select the repo and branch (e.g. `main`).

## 3. Service settings

- **Root directory:** leave **empty** (repo root), unless your app lives in a subfolder — then set that folder.
- **Start command** (if not picked up from `railway.toml`):

  ```bash
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```

- Railway sets **`PORT`** automatically.

## 4. Environment variables (minimum)

Add in **Variables** (same for Production):

| Name | Notes |
|------|--------|
| `GOOGLE_CLOUD_PROJECT` | e.g. `heyitdonald` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to JSON **after** you add the file (see below) |
| `ANTHROPIC_API_KEY` | Required for research |
| `FIRECRAWL_API_KEY` | Required for research |
| `FRONTEND_URL` | Your Vercel URL, e.g. `https://your-app.vercel.app` (CORS) |

**Service account (Firestore)**

Easiest on Railway: add a variable **`GOOGLE_APPLICATION_CREDENTIALS_JSON`** and paste the **entire JSON** from Firebase (Project settings → Service accounts → Generate key). The API writes it to a temp file at startup.

Alternatively set **`GOOGLE_APPLICATION_CREDENTIALS`** to a path if you mount or bake in the JSON file.

Also list optional: REDIS_URL, CELERY_* if using worker

FIRESTORE_DISABLED - don't set in prod

ELEVENLABS_API_KEY if needed

## 5. Redis + Celery (optional for first deploy)

For a **minimal** API-only deploy, you can set:

- `CELERY_DISABLED=1`  
- `REDIS_DISABLED=1`  

Then `POST /api/research` runs **inline** in the web process (no Redis). Add Redis + worker later.

## 6. Deploy

Trigger deploy. Open **Settings → Networking → Generate Domain** to get a public URL like `https://xxx.up.railway.app`.

Use that as **`NEXT_PUBLIC_API_URL`** on Vercel.

## 7. Health check

- `GET https://<your-url>/health`  
- `GET https://<your-url>/ready` (Firestore/Redis checks)

---

## Second service: Celery worker (later)

- Same repo, same env vars.
- Start command: `celery -A backend.celery_app worker -l info`
- Add **Redis** plugin and set `REDIS_URL` on both services; unset `CELERY_DISABLED` / `REDIS_DISABLED` on API when ready.
