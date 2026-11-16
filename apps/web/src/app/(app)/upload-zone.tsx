"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type DragEvent, useRef, useState } from "react";
import { apiFetch } from "@/lib/browser-api";

type Item = {
  key: string;
  name: string;
  state: "waiting" | "reading" | "done" | "failed";
  id?: string;
  status?: string;
  error?: string;
};

export default function UploadZone() {
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [profile, setProfile] = useState("my");
  const [dragging, setDragging] = useState(false);

  // One shared queue and one worker: reading a receipt is CPU-heavy and the API runs on a
  // small server, so a second drop joins the queue instead of starting a parallel upload.
  const queue = useRef<{ key: string; file: File; profile: string }[]>([]);
  const busy = useRef(false);

  const update = (key: string, patch: Partial<Item>) =>
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)));

  async function upload(files: File[]) {
    const batch = files.map((file) => ({ key: crypto.randomUUID(), file, profile }));
    setItems((prev) => [...batch.map(({ key, file }): Item => ({ key, name: file.name, state: "waiting" })), ...prev]);
    queue.current.push(...batch);
    if (busy.current) return; // the running worker will pick these up
    busy.current = true;
    let next;
    while ((next = queue.current.shift())) {
      const { key, file, profile } = next;
      update(key, { state: "reading" });
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await apiFetch(`/receipts?profile=${encodeURIComponent(profile)}`, {
          method: "POST",
          body: form,
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          // FastAPI sends a list for field errors; only show detail when it's a sentence.
          throw new Error(typeof body.detail === "string" ? body.detail : `Upload failed (${res.status})`);
        }
        update(key, { state: "done", id: body.id, status: body.status, name: body.merchant ?? file.name });
      } catch (e) {
        const error = e instanceof TypeError ? "Couldn't reach the API" : (e as Error).message;
        update(key, { state: "failed", error });
      }
    }
    busy.current = false;
    router.refresh(); // new counts on the dashboard and in the sidebar
  }

  function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    upload([...event.dataTransfer.files]);
  }

  return (
    <section aria-label="Upload receipts" className="flex flex-col gap-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        className={`flex flex-wrap items-center gap-5 rounded-2xl border-2 border-dashed px-6 py-5 ${
          dragging ? "border-blue-500 bg-blue-50" : "border-blue-200 bg-white"
        }`}
      >
        <span aria-hidden className="flex size-14 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 16V4M7 9l5-5 5 5M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
          </svg>
        </span>
        <div className="min-w-56 flex-1">
          <h2 className="font-semibold">Drop receipts here</h2>
          <p className="text-sm text-gray-600">JPEG, PNG or WebP up to 10 MB · several at once</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          Region
          <select
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            className="min-h-11 rounded-lg border border-gray-300 bg-white px-2"
          >
            <option value="my">Malaysia</option>
            <option value="ch">Switzerland</option>
            <option value="generic">Other / unknown</option>
          </select>
        </label>
        <label className="flex min-h-11 cursor-pointer items-center rounded-lg bg-gray-900 px-4 text-sm font-semibold text-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2 hover:bg-gray-700">
          Choose files
          <input
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(e) => {
              upload([...(e.target.files ?? [])]);
              e.target.value = ""; // so choosing the same file again still uploads it
            }}
          />
        </label>
      </div>
      {items.length > 0 && (
        <ul aria-live="polite" className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white text-sm">
          {items.map((it) => {
            const [text, tone] =
              it.state === "failed"
                ? [it.error, "text-red-700"]
                : it.state === "done"
                  ? it.status === "confirmed"
                    ? ["Confirmed by checks", "text-green-700"]
                    : ["Needs review", "text-amber-800"]
                  : [it.state === "reading" ? "Reading…" : "Waiting…", "text-gray-500"];
            return (
              <li key={it.key} className="flex items-center justify-between gap-4 px-4 py-3">
                {it.id ? (
                  <Link href={`/receipts/${it.id}`} className="truncate font-medium hover:underline">
                    {it.name}
                  </Link>
                ) : (
                  <span className="truncate">{it.name}</span>
                )}
                <span className={`shrink-0 ${tone}`}>{text}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
