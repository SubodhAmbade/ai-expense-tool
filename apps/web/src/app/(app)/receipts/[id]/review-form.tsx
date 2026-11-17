"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { CATEGORIES, label, type Receipt } from "@/lib/api";
import { apiFetch } from "@/lib/browser-api";

const FIELDS = [
  { name: "merchant", label: "Merchant", type: "text", wide: true },
  { name: "receipt_date", label: "Date", type: "date" },
  { name: "currency", label: "Currency (e.g. MYR)", type: "text" },
  { name: "net_amount", label: "Subtotal", type: "text" },
  { name: "tax_amount", label: "Tax", type: "text" },
  { name: "total_amount", label: "Total", type: "text" },
] as const;

// Only the editable fields reach the browser; the OCR text and check details stay on the server.
type Editable = Pick<
  Receipt,
  "id" | "merchant" | "receipt_date" | "currency" | "net_amount" | "tax_amount" | "total_amount" | "category" | "note"
>;

const input = "min-h-11 rounded-lg border border-gray-300 bg-white px-3 text-base text-gray-900";

export default function ReviewForm({ receipt, nextHref }: { receipt: Editable; nextHref: string }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [attested, setAttested] = useState(false); // a person vouches for every receipt they confirm
  const hasNext = nextHref !== "/review";

  // False once this form is gone (the reviewer moved to another receipt mid-save), so a late
  // save doesn't drag them back. The <Link>s already prefetch the next receipt.
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

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
      res = await apiFetch(`/receipts/${receipt.id}`, {
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
    if (active.current) router.push(nextHref); // not if the reviewer has already moved on
    router.refresh(); // the sidebar count changes either way
  }

  return (
    <form onSubmit={save} className="flex flex-1 flex-col gap-4 text-sm">
      <div className="grid gap-4 sm:grid-cols-2">
        {FIELDS.map((f) => (
          <label key={f.name} className={`flex flex-col gap-1.5 font-medium text-gray-700 ${"wide" in f ? "sm:col-span-2" : ""}`}>
            {f.label}
            <input name={f.name} type={f.type} defaultValue={receipt[f.name] ?? ""} className={`${input} font-normal tabular-nums`} />
          </label>
        ))}
        <label className="flex flex-col gap-1.5 font-medium text-gray-700 sm:col-span-2">
          Category
          <select name="category" defaultValue={receipt.category ?? "other"} className={`${input} font-normal capitalize`}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {label(c)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 font-medium text-gray-700 sm:col-span-2">
          Note (optional)
          <textarea
            name="note"
            rows={2}
            maxLength={500}
            defaultValue={receipt.note ?? ""}
            placeholder="e.g. Client lunch with Acme; GST added by hand"
            className={`${input} py-2 font-normal`}
          />
        </label>
      </div>
      {/* No name, so it isn't sent: confirming is the record. `required` also stops Enter from skipping it. */}
      <label className="flex min-h-11 items-center gap-3 font-medium text-gray-800">
        <input
          type="checkbox"
          required
          checked={attested}
          onChange={(e) => setAttested(e.target.checked)}
          className="size-5 accent-blue-700"
        />
        I confirm these details match the receipt
      </label>
      {error && <p className="text-red-700">{error}</p>}
      <div className="mt-auto flex flex-wrap items-center justify-end gap-3 border-t border-gray-100 pt-4">
        {hasNext && (
          <Link
            href={nextHref}
            aria-disabled={saving}
            onClick={(e) => saving && e.preventDefault()} // skipping mid-save would race the save's own move on
            className={`flex min-h-11 items-center rounded-lg border border-gray-300 px-4 font-medium hover:bg-gray-50 ${saving ? "pointer-events-none opacity-50" : ""}`}
          >
            Skip
          </Link>
        )}
        <button
          disabled={saving || !attested}
          className="min-h-11 rounded-lg bg-blue-700 px-5 font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
        >
          {saving ? "Saving…" : hasNext ? "Confirm & next" : "Confirm"}
        </button>
      </div>
    </form>
  );
}
