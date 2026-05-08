# Deploy with Vercel CLI

The Vercel CLI is installed as a **devDependency** (`npm run vercel`).

## One-time setup

1. **Install deps** (from this folder):

   ```bash
   cd frontend
   npm install
   ```

2. **Log in** (opens the browser — you must sign in):

   ```bash
   npx vercel login
   ```

3. **Link the project** (first time only):

   ```bash
   npx vercel link
   ```

   Follow the prompts: create a new project or link to an existing one on your Vercel account.

## Environment variables

Easiest: **Vercel dashboard → Project → Settings → Environment Variables** (Production / Preview / Development).

Or CLI (example):

```bash
npx vercel env add NEXT_PUBLIC_API_URL
```

Set at least:

- `NEXT_PUBLIC_API_URL` — your production API URL (e.g. `https://your-api.up.railway.app`)
- `NEXT_PUBLIC_FIREBASE_*` — from Firebase web app config
- `NEXT_PUBLIC_ELEVENLABS_*` — agent id, token mode, etc.

### Sentry (`@sentry/nextjs`)

Runtime (Issues + tracing + replay):

- `NEXT_PUBLIC_SENTRY_DSN` — browser DSN (public)
- `SENTRY_DSN` — optional server/edge DSN; if unset, server falls back to `NEXT_PUBLIC_SENTRY_DSN`

Build (source maps on `next build` — recommended for production):

- `SENTRY_AUTH_TOKEN` — token with `project:releases` and `org:read` ([auth tokens](https://sentry.io/settings/auth-tokens/))
- `SENTRY_ORG` — organization slug
- `SENTRY_PROJECT` — project slug

You can put build secrets in `.env.sentry-build-plugin` locally (gitignored) or only in Vercel **Environment Variables** for Production.

Interactive setup (optional): `npx @sentry/wizard@latest -i nextjs`

## Deploy

- **Preview (branch / PR):**

  ```bash
  npm run vercel:deploy
  ```

- **Production:**

  ```bash
  npm run vercel:prod
  ```

Or: `npx vercel --prod` from this directory.

## Notes

- Deploy **from the `frontend` folder** so Next.js is the project root.
- `.vercel/` is gitignored — it stores the linked project id locally.
- Add your Vercel domain under **Firebase → Project settings → Authorized domains** if you use Google sign-in / Analytics.
