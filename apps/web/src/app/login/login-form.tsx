"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { IDLE_KEY } from "@/lib/api";
import { supabaseBrowser } from "@/lib/browser-api";

const input = "min-h-11 rounded-lg border border-gray-300 px-3 text-base text-gray-900";

export default function LoginForm({ idle }: { idle: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // onSubmit rather than a form action: a form action clears the inputs even when sign-in fails.
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    const { error } = await supabaseBrowser().auth.signInWithPassword({
      email: String(form.get("email")),
      password: String(form.get("password")),
    });
    if (error) {
      // Supabase says "Invalid login credentials" for both a wrong email and a wrong password.
      setError(error.status === 400 ? "Wrong email or password." : "Couldn't sign in. Try again in a moment.");
      setBusy(false);
      return;
    }
    try {
      localStorage.setItem(IDLE_KEY, String(Date.now())); // a fresh sign-in isn't idle
    } catch {}
    router.replace("/");
    router.refresh();
  }

  return (
    <form onSubmit={signIn} className="flex w-full max-w-sm flex-col gap-5">
      <h2 className="text-3xl font-semibold tracking-tight">Sign in</h2>
      {idle && (
        <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          You were signed out after 15 minutes without activity.
        </p>
      )}
      <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
        Email
        <input name="email" type="email" autoComplete="email" required className={input} />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
        Password
        <input name="password" type="password" autoComplete="current-password" required className={input} />
      </label>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button
        disabled={busy}
        className="min-h-11 rounded-lg bg-blue-700 px-5 font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
