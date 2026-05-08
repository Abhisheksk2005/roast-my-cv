"use client";

import { useEffect } from "react";
import { initFirebaseAnalytics } from "@/lib/firebase";

/**
 * Mount once in the root layout to initialize Firebase Analytics on the client.
 * Renders nothing.
 */
export function FirebaseRoot() {
  useEffect(() => {
    void initFirebaseAnalytics();
  }, []);
  return null;
}
