/**
 * Firebase Web SDK (client-only).
 * Values come from NEXT_PUBLIC_* env vars — never hardcode keys in source.
 */
import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import { getAnalytics, isSupported, type Analytics } from "firebase/analytics";

function firebaseConfig() {
  return {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
    measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
  };
}

function isConfigured(): boolean {
  const c = firebaseConfig();
  return Boolean(c.apiKey && c.projectId && c.appId);
}

/** Returns the Firebase app on the client, or null if env is missing / SSR. */
export function getFirebaseApp(): FirebaseApp | null {
  if (typeof window === "undefined") return null;
  if (!isConfigured()) return null;
  const config = firebaseConfig();
  if (!getApps().length) {
    return initializeApp(config);
  }
  return getApps()[0]!;
}

let analyticsSingleton: Analytics | null | undefined;

/** Initialize Analytics once (browser + supported environments only). */
export async function initFirebaseAnalytics(): Promise<Analytics | null> {
  if (typeof window === "undefined") return null;
  if (analyticsSingleton !== undefined) return analyticsSingleton;

  const app = getFirebaseApp();
  if (!app) {
    analyticsSingleton = null;
    return null;
  }

  try {
    if (!(await isSupported())) {
      analyticsSingleton = null;
      return null;
    }
    analyticsSingleton = getAnalytics(app);
    return analyticsSingleton;
  } catch {
    analyticsSingleton = null;
    return null;
  }
}
