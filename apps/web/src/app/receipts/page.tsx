import Link from "next/link";
import { Suspense } from "react";
import { API_URL, label, type Receipt } from "@/lib/api";

const FILTERS = [
  { name: "All", status: undefined },
  { name: "Needs review", status: "needs_review" },
  { name: "Confirmed", status: "confirmed" },
];

export default function ReceiptsPage(props: PageProps<"/receipts">) {
  return (
    <main className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Receipts</h1>
        <a href={`${API_URL}/receipts/export.csv`} className="rounded border px-3 py-1.5 text-sm">
          Export confirmed (CSV)
        </a>
      </div>
      <Suspense fallback={<p className="text-sm text-zinc-500">Loading receipts…</p>}>
        <ReceiptList searchParams={props.searchParams} />
      </Suspense>
    </main>
  );
}

async function ReceiptList({ searchParams }: { searchParams: PageProps<"/receipts">["searchParams"] }) {
  const { status } = await searchParams;
  const filter = FILTERS.find((f) => f.status === status) ?? FILTERS[0];
  let receipts: Receipt[];
  try {
    const res = await fetch(`${API_URL}/receipts${filter.status ? `?status=${filter.status}` : ""}`);
    if (!res.ok) throw new Error();
    receipts = await res.json();
  } catch {
    return <p className="text-sm text-red-600">Couldn&apos;t load receipts. Is the API running?</p>;
  }

  return (
    <>
      <div className="flex gap-2 text-sm">
        {FILTERS.map((f) => (
          <Link
            key={f.name}
            href={f.status ? `/receipts?status=${f.status}` : "/receipts"}
            className={`rounded-full px-3 py-1 ${f === filter ? "bg-zinc-900 text-white dark:bg-white dark:text-black" : "border"}`}
          >
            {f.name}
          </Link>
        ))}
      </div>
      {receipts.length === 0 ? (
        <p className="text-sm text-zinc-500">Nothing here yet.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="text-zinc-500">
            <tr>
              <th className="py-2">Date</th>
              <th>Merchant</th>
              <th>Category</th>
              <th className="text-right">Total</th>
              <th className="pl-6">Status</th>
            </tr>
          </thead>
          <tbody>
            {receipts.map((r) => (
              <tr key={r.id} className="border-t border-zinc-200 dark:border-zinc-800">
                <td className="py-2">{r.receipt_date ?? "—"}</td>
                <td>
                  <Link href={`/receipts/${r.id}`} className="underline">
                    {r.merchant ?? "Unknown merchant"}
                  </Link>
                </td>
                <td className="capitalize">{label(r.category)}</td>
                <td className="text-right font-mono">
                  {r.total_amount ?? "—"} {r.currency ?? ""}
                </td>
                <td className="pl-6">
                  {r.status === "confirmed" ? (
                    <span className="text-green-700 dark:text-green-400">Confirmed</span>
                  ) : (
                    <span className="text-amber-700 dark:text-amber-400">
                      Needs review ({r.validation_errors.length})
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
