import Link from "next/link";
import { Suspense } from "react";
import { fetchReceipts } from "@/lib/server-api";
import ReceiptTable from "../receipt-table";

const FILTERS = [
  { name: "All", status: undefined },
  { name: "Needs review", status: "needs_review" },
  { name: "Confirmed", status: "confirmed" },
] as const;

export default function ReceiptsPage(props: PageProps<"/receipts">) {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">All receipts</h1>
      <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-gray-100" />}>
        <ReceiptList searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function ReceiptList({ searchParams }: { searchParams: PageProps<"/receipts">["searchParams"] }) {
  const { status } = await searchParams;
  const filter = FILTERS.find((f) => f.status === status) ?? FILTERS[0];
  const receipts = await fetchReceipts(filter.status);
  if (!receipts) {
    return <p className="text-sm text-red-700">Couldn&apos;t load receipts. Is the API running?</p>;
  }

  return (
    <>
      <div className="flex flex-wrap gap-2 text-sm">
        {FILTERS.map((f) => (
          <Link
            key={f.name}
            href={f.status ? `/receipts?status=${f.status}` : "/receipts"}
            aria-current={f === filter ? "page" : undefined}
            className={`flex min-h-11 items-center rounded-full px-4 ${
              f === filter ? "bg-gray-900 font-semibold text-white" : "border border-gray-300 bg-white hover:bg-gray-50"
            }`}
          >
            {f.name}
          </Link>
        ))}
      </div>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {receipts.length ? (
          <ReceiptTable receipts={receipts} />
        ) : (
          <p className="px-5 py-8 text-sm text-gray-500">Nothing here yet.</p>
        )}
      </section>
    </>
  );
}
