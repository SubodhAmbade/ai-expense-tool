"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { API_URL } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function upload(form: FormData) {
    setBusy(true);
    setError("");
    try {
      const profile = encodeURIComponent(String(form.get("profile")));
      const res = await fetch(`${API_URL}/receipts?profile=${profile}`, { method: "POST", body: form });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail ?? `Upload failed (${res.status})`);
      router.push(`/receipts/${body.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed. Is the API running?");
      setBusy(false);
    }
  }

  return (
    <main className="flex max-w-md flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Upload a receipt</h1>
        <p className="mt-1 text-sm text-zinc-500">
          JPEG, PNG or WebP, up to 10 MB. Reading takes a few seconds.
        </p>
      </div>
      <form action={upload} className="flex flex-col gap-4">
        <input
          name="file"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          required
          className="text-sm"
        />
        <label className="flex flex-col gap-1 text-sm">
          Region
          <select name="profile" defaultValue="my" className="rounded border px-2 py-1">
            <option value="my">Malaysia</option>
            <option value="ch">Switzerland</option>
            <option value="generic">Other / unknown</option>
          </select>
        </label>
        <button
          disabled={busy}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
        >
          {busy ? "Reading receipt…" : "Upload"}
        </button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </main>
  );
}
