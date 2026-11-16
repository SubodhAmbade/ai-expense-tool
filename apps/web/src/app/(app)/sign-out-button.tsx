"use client";

import { useRouter } from "next/navigation";
import { supabaseBrowser } from "@/lib/browser-api";

export default function SignOutButton() {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={async () => {
        const auth = supabaseBrowser().auth;
        const { error } = await auth.signOut(); // also ends the session on Supabase's side
        if (error) await auth.signOut({ scope: "local" }); // offline: at least sign out here
        router.replace("/login");
        router.refresh();
      }}
      className="min-h-11 shrink-0 rounded-lg px-3 text-sm font-medium text-gray-700 hover:bg-gray-100"
    >
      Sign out
    </button>
  );
}
