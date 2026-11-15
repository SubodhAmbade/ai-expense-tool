import Link from "next/link";
import { Suspense } from "react";
import { API_URL, fetchReceipts, label, type Receipt } from "@/lib/api";
import ReceiptTable from "./receipt-table";
import UploadZone from "./upload-zone";

export default function Dashboard() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <a
          href={`${API_URL}/receipts/export.csv`}
          className="flex min-h-11 items-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-medium hover:bg-gray-50"
        >
          Export CSV
        </a>
      </header>
      <UploadZone />
      <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-gray-100" />}>
        <Overview />
      </Suspense>
    </div>
  );
}

const cents = (amount: Receipt["total_amount"]) => Math.round(Number(amount) * 100);
const money = (c: number) => (c / 100).toLocaleString("en", { minimumFractionDigits: 2 });

async function Overview() {
  let receipts: Receipt[];
  try {
    receipts = await fetchReceipts();
  } catch {
    return <p className="text-sm text-red-700">Couldn&apos;t load receipts. Is the API running?</p>;
  }

  const now = new Date();
  const month = now.toISOString().slice(0, 7); // "2026-11", in UTC like created_at
  const queue = receipts.filter((r) => r.status === "needs_review").reverse(); // oldest first
  const uploaded = receipts.filter((r) => r.created_at.startsWith(month));
  const autoAccepted = uploaded.filter((r) => r.status === "confirmed" && !r.confirmed_at).length;

  // Confirmed spend this month, kept apart per currency: MYR and CHF are never added together.
  const spend = new Map<string, number>();
  const byCategory = new Map<string, { currency: string; category: string; cents: number }>();
  for (const r of receipts) {
    if (r.status !== "confirmed" || !r.currency || r.total_amount == null || !r.receipt_date?.startsWith(month)) continue;
    spend.set(r.currency, (spend.get(r.currency) ?? 0) + cents(r.total_amount));
    const key = `${r.currency} ${r.category}`;
    const row = byCategory.get(key) ?? { currency: r.currency, category: r.category ?? "other", cents: 0 };
    byCategory.set(key, { ...row, cents: row.cents + cents(r.total_amount) });
  }
  const categories = [...byCategory.values()].sort((a, b) => b.cents - a.cents);
  const top = new Map<string, number>(); // biggest category per currency, so each bar is relative to its own currency
  for (const c of categories) if (!top.has(c.currency)) top.set(c.currency, c.cents);

  const stats = [
    { label: "Needs review", value: String(queue.length), note: queue.length ? `Oldest from ${queue[0].created_at.slice(0, 10)}` : "All caught up" },
    { label: "Uploaded this month", value: String(uploaded.length), note: `${uploaded.length - autoAccepted} needed a person` },
    {
      label: "Spend this month",
      value: [...spend].map(([currency, c]) => `${currency} ${money(c)}`).join("\n") || "—",
      note: "Confirmed, by receipt date",
    },
    {
      label: "Auto-accepted",
      value: uploaded.length ? `${Math.round((100 * autoAccepted) / uploaded.length)}%` : "—",
      note: "Passed every check this month",
    },
  ];

  return (
    <>
      <section aria-label={now.toLocaleString("en", { month: "long", year: "numeric", timeZone: "UTC" })} className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col gap-1 rounded-xl border border-gray-200 bg-white p-5">
            <span className="text-sm text-gray-600">{s.label}</span>
            <span className="text-2xl font-bold tracking-tight whitespace-pre-line tabular-nums">{s.value}</span>
            <span className="text-xs text-gray-500">{s.note}</span>
          </div>
        ))}
      </section>

      <div className="flex flex-wrap items-start gap-6">
        <section aria-labelledby="queue-h" className="min-w-0 flex-[999_1_520px] overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
            <h2 id="queue-h" className="font-semibold">Needs review</h2>
            {queue.length > 0 && (
              <Link href={`/receipts/${queue[0].id}`} className="text-sm font-medium text-blue-700 hover:underline">
                Start reviewing
              </Link>
            )}
          </div>
          {queue.length ? (
            <ReceiptTable receipts={queue.slice(0, 5)} />
          ) : (
            <p className="px-5 py-8 text-sm text-gray-500">Nothing waiting. New uploads that fail a check show up here.</p>
          )}
        </section>

        <section aria-labelledby="cat-h" className="flex min-w-0 flex-[1_1_300px] flex-col gap-4 rounded-xl border border-gray-200 bg-white px-5 py-4">
          <h2 id="cat-h" className="font-semibold">Spend by category</h2>
          {categories.length === 0 && <p className="text-sm text-gray-500">No confirmed receipts dated this month yet.</p>}
          {categories.slice(0, 6).map((c) => (
            <div key={`${c.currency} ${c.category}`} className="flex flex-col gap-1.5">
              <div className="flex justify-between gap-3 text-sm">
                <span className="capitalize">{label(c.category)}</span>
                <span className="text-gray-700 tabular-nums">
                  {c.currency} {money(c.cents)}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                <div className="h-2 rounded-full bg-blue-700" style={{ width: `${(100 * c.cents) / top.get(c.currency)!}%` }} />
              </div>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
