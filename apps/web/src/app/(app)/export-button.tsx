"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/browser-api";

// A plain link can't send the sign-in token, so fetch the CSV with it and save it from memory.
export default function ExportButton({ className, label = "Export CSV" }: { className: string; label?: string }) {
  const [error, setError] = useState("");

  async function download() {
    setError("");
    try {
      const res = await apiFetch("/receipts/export.csv");
      if (!res.ok) throw new Error();
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: "receipts.csv" });
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Couldn't download. Is the API running?");
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button type="button" onClick={download} className={className}>
        {label}
      </button>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </div>
  );
}
