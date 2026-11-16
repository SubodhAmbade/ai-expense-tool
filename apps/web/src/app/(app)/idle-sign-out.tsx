"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { IDLE_KEY } from "@/lib/api";
import { supabaseBrowser } from "@/lib/browser-api";

const IDLE_MS = 15 * 60 * 1000;
const EVENTS = ["pointerdown", "keydown", "scroll", "touchstart"] as const;

// Signs out after 15 minutes with no clicks, typing or scrolling in any tab. Supabase's own
// inactivity timeout is a paid feature, so the app enforces it. The last-active time is shared
// through localStorage; if that's unavailable (private mode), each tab keeps its own.
export default function IdleSignOut() {
  const router = useRouter();

  useEffect(() => {
    let local = 0; // this tab's last activity
    const read = () => {
      try {
        return Math.max(local, Number(localStorage.getItem(IDLE_KEY)) || 0);
      } catch {
        return local;
      }
    };
    const touch = () => {
      local = Date.now();
      try {
        localStorage.setItem(IDLE_KEY, String(local));
      } catch {}
    };
    const check = async () => {
      if (Date.now() - read() < IDLE_MS) return;
      clearInterval(timer);
      await supabaseBrowser().auth.signOut({ scope: "local" }); // ends this browser's session
      router.replace("/login?reason=idle");
    };

    const timer = setInterval(check, 30_000);
    // Coming back to an old tab, or reopening the app after a long break, counts as idle too.
    const last = read();
    if (last && Date.now() - last >= IDLE_MS) check();
    else touch();
    EVENTS.forEach((e) => window.addEventListener(e, touch, { passive: true }));
    return () => {
      clearInterval(timer);
      EVENTS.forEach((e) => window.removeEventListener(e, touch));
    };
  }, [router]);

  return null;
}
