import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

/**
 * Next.js matches allowedDevOrigins against the Origin *hostname* only (see block-cross-site-dev).
 * Full URLs like https://foo.ngrok-free.dev never match — use hostname, or http(s) URL and we strip it.
 */
function toAllowedDevOriginHost(entry: string): string {
  const t = entry.trim().replace(/\/$/, "");
  if (!t) return "";
  try {
    if (/^https?:\/\//i.test(t)) {
      return new URL(t).hostname.toLowerCase();
    }
  } catch {
    /* fall through */
  }
  return t.toLowerCase();
}

/** Comma-separated URLs or hostnames (e.g. https://abc.ngrok-free.app). */
function devOriginsFromEnv(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((s) => toAllowedDevOriginHost(s))
    .filter(Boolean);
}

const allowedDevOrigins = Array.from(
  new Set([
    ...devOriginsFromEnv(process.env.NGROK_URL),
    ...devOriginsFromEnv(process.env.ALLOWED_DEV_ORIGINS),
  ])
);

const backendProxy =
  (process.env.BACKEND_PROXY_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Dev-only: allow browser requests when the app is reached via ngrok / another tunnel.
  ...(allowedDevOrigins.length > 0 ? { allowedDevOrigins } : {}),
  // Browser hits /api/* on the Next host; we forward to FastAPI (fixes 404 when NEXT_PUBLIC_API_URL was set to the frontend/ngrok URL).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendProxy}/api/:path*` }];
  },
};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  authToken: process.env.SENTRY_AUTH_TOKEN,

  widenClientFileUpload: true,

  // Proxy to reduce ad-blocker drops (exclude in middleware if you add auth middleware)
  tunnelRoute: "/monitoring",

  silent: !process.env.CI,
});
