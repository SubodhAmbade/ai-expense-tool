import Link from "next/link";
import { Suspense } from "react";
import { fetchReceipts, type Receipt } from "@/lib/api";
import ReceiptTable from "../receipt-table";

export default function ReviewQueuePage() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Review queue</h1>
        <p className="mt-1 text-sm text-gray-600">Receipts the checks couldn&apos;t confirm, oldest first.</p>
      </div>
      <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-gray-100" />}>
        <Queue />
      </Suspense>
    </div>
  );
}

async function Queue() {
  let queue: Receipt[];
  try {
    queue = (await fetchReceipts("needs_review")).reverse();
  } catch {
    return <p className="text-sm text-red-700">Couldn&apos;t load the queue. Is the API running?</p>;
  }
  if (queue.length === 0) {
    return (
      <p className="rounded-xl border border-gray-200 bg-white px-5 py-8 text-sm text-gray-600">
        All caught up. Nothing needs checking.
      </p>
    );
  }
  return (
    <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
        <h2 className="font-semibold">{queue.length} waiting</h2>
        <Link
          href={`/receipts/${queue[0].id}`}
          className="flex min-h-11 items-center rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800"
        >
          Start reviewing
        </Link>
      </div>
      <ReceiptTable receipts={queue} />
    </section>
  );
}
