import { Suspense } from "react";
import { fetchReceipts } from "@/lib/server-api";
import ExportButton from "../export-button";

export default function ExportPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Export</h1>
        <p className="mt-1 text-sm text-gray-600">
          A CSV of every confirmed receipt, ready for an accounting tool. Receipts still waiting for review are left out.
        </p>
      </div>
      <Suspense fallback={<div className="h-40 animate-pulse rounded-xl bg-gray-100" />}>
        <Summary />
      </Suspense>
    </div>
  );
}

async function Summary() {
  const confirmed = await fetchReceipts("confirmed");
  if (!confirmed) {
    return <p className="text-sm text-red-700">Couldn&apos;t load receipts. Is the API running?</p>;
  }
  const currencies = [...new Set(confirmed.map((r) => r.currency ?? "no currency"))].join(", ");

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-6">
      <p className="text-3xl font-bold tracking-tight">{confirmed.length} confirmed receipts</p>
      {confirmed.length > 0 && <p className="text-sm text-gray-600">Currencies: {currencies}</p>}
      <p className="text-sm text-gray-600">
        Columns: id, date, merchant, category, currency, net, tax, total. Amounts are exact, never rounded or converted.
      </p>
      <ExportButton
        label="Download CSV"
        className="flex min-h-11 items-center rounded-lg bg-blue-700 px-5 text-sm font-semibold text-white hover:bg-blue-800"
      />
    </section>
  );
}
