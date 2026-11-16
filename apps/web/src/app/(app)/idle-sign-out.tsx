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
// Also: if another tab signed out or into a different account, this tab's page shows someone
// else's receipts, so it reloads (checked when the tab regains focus and every 30 seconds).
export default function IdleSignOut({ userId }: { userId: string }) {
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
      const last = read();
      if (last && Date.now() - last >= IDLE_MS) return check(); // waking a sleeping laptop isn't activity
      local = Date.now();
      try {
        localStorage.setItem(IDLE_KEY, String(local));
      } catch {}
    };
    let ending = false;
    const sameUser = async () => {
      const now = (await supabaseBrowser().auth.getSession()).data.session?.user.id;
      if (!userId || now === userId || ending) return; // !userId: page rendered without one; never loop
      ending = true;
      clearInterval(timer);
      // A full reload, so the other user's page is dropped, not just re-rendered.
      window.location.assign(now ? "/" : "/login");
    };
    const check = async () => {
      await sameUser();
      if (ending || Date.now() - read() < IDLE_MS) return;
      ending = true;
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
    window.addEventListener("focus", sameUser);
    return () => {
      clearInterval(timer);
      EVENTS.forEach((e) => window.removeEventListener(e, touch));
      window.removeEventListener("focus", sameUser);
    };
  }, [router, userId]);

  return null;
}
