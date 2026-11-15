"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { API_URL, CATEGORIES, label, type Receipt } from "@/lib/api";

const FIELDS = [
  { name: "merchant", label: "Merchant", type: "text" },
  { name: "receipt_date", label: "Date", type: "date" },
  { name: "currency", label: "Currency (e.g. MYR)", type: "text" },
  { name: "net_amount", label: "Subtotal", type: "text" },
  { name: "tax_amount", label: "Tax", type: "text" },
  { name: "total_amount", label: "Total", type: "text" },
] as const;

// Only the editable fields reach the browser; the OCR text and check details stay on the server.
type Editable = Pick<
  Receipt,
  "id" | "merchant" | "receipt_date" | "currency" | "net_amount" | "tax_amount" | "total_amount" | "category"
>;

export default function ReviewForm({ receipt }: { receipt: Editable }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // onSubmit rather than a form action: a form action clears the reviewer's edits even when saving fails.
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return; // a second click mustn't race the first save
    setSaving(true);
    setError("");
    // Empty fields are sent as null; amounts stay strings so the API keeps them exact.
    const body = Object.fromEntries(
      [...new FormData(event.currentTarget).entries()].map(([k, v]) => [
        k,
        String(v).trim() === "" ? null : String(v).trim(),
      ]),
    );
    let res: Response;
    try {
      res = await fetch(`${API_URL}/receipts/${receipt.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      setError("Couldn't reach the API. Check it's running, then try again.");
      setSaving(false);
      return;
    }
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({}))).detail;
      setError(typeof detail === "string" ? detail : "Some fields are invalid; check the values.");
      setSaving(false);
      return;
    }
    router.push("/receipts?status=needs_review");
    router.refresh();
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-3 text-sm">
      {FIELDS.map((f) => (
        <label key={f.name} className="flex flex-col gap-1">
          {f.label}
          <input
            name={f.name}
            type={f.type}
            defaultValue={receipt[f.name] ?? ""}
            className="rounded border px-2 py-1 font-mono"
          />
        </label>
      ))}
      <label className="flex flex-col gap-1">
        Category
        <select
          name="category"
          defaultValue={receipt.category ?? "other"}
          className="rounded border px-2 py-1 capitalize"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {label(c)}
            </option>
          ))}
        </select>
      </label>
      <button
        disabled={saving}
        className="mt-2 rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
      >
        {saving ? "Saving…" : "Confirm"}
      </button>
      {error && <p className="text-red-600">{error}</p>}
    </form>
  );
}
