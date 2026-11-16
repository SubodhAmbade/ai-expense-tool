import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import type { Receipt } from "@/lib/api";
import { apiGet, fetchReceipts } from "@/lib/server-api";
import ReviewForm from "./review-form";

export default function ReceiptPage(props: PageProps<"/receipts/[id]">) {
  return (
    <Suspense fallback={<div className="h-[70vh] animate-pulse rounded-xl bg-gray-100" />}>
      <ReceiptDetail params={props.params} />
    </Suspense>
  );
}

async function ReceiptDetail({ params }: { params: PageProps<"/receipts/[id]">["params"] }) {
  const { id } = await params;
  const [res, waiting] = await Promise.all([
    apiGet(`/receipts/${encodeURIComponent(id)}`),
    fetchReceipts("needs_review"),
  ]);
  if (res?.status === 404 || res?.status === 422) notFound(); // someone else's receipt is a 404 too
  if (!res?.ok) {
    return <p className="text-sm text-red-700">Couldn&apos;t load this receipt. Is the API running?</p>;
  }
  const queue = [...(waiting ?? [])].reverse(); // oldest first, same as the queue page
  const receipt: Receipt = await res.json();

  // Where this receipt sits in the queue. Confirming moves on to the next one still waiting,
  // wrapping round to the oldest; a receipt that isn't in the queue moves on to the oldest.
  const at = queue.findIndex((r) => r.id === id);
  const prev = at > 0 ? queue[at - 1] : undefined;
  const next = queue[at + 1] ?? queue.find((r) => r.id !== id);
  const arrow = "flex size-11 items-center justify-center rounded-lg border border-gray-300 bg-white hover:bg-gray-50";

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-gray-600">
            {at >= 0 ? (
              <>
                <Link href="/review" className="hover:underline">Review queue</Link> · {at + 1} of {queue.length}
              </>
            ) : (
              <Link href="/receipts" className="hover:underline">All receipts</Link>
            )}
          </p>
          <h1 className="truncate text-2xl font-bold tracking-tight">{receipt.merchant ?? "Unknown merchant"}</h1>
        </div>
        {at >= 0 && (
          <nav aria-label="Queue" className="flex gap-2">
            {prev && (
              <Link href={`/receipts/${prev.id}`} aria-label="Previous receipt" className={arrow}>
                <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
              </Link>
            )}
            {next && (
              <Link href={`/receipts/${next.id}`} aria-label="Next receipt" className={arrow}>
                <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
              </Link>
            )}
          </nav>
        )}
      </header>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="flex items-center justify-center rounded-xl bg-gray-200 p-4 lg:h-[calc(100vh-10rem)]">
          {/* A short-lived signed link from private storage, so next/image can't optimise it. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={receipt.image_url} alt="Receipt photo" className="max-h-full max-w-full rounded object-contain shadow" />
        </div>
        <section aria-label="Extracted fields" className="flex flex-col gap-5 rounded-xl border border-gray-200 bg-white p-6">
          {receipt.status === "needs_review" ? (
            <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-semibold">Check before confirming</p>
              <ul className="mt-1 list-disc pl-5">
                {receipt.validation_errors.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-green-700">Confirmed. You can still correct it.</p>
          )}
          {/* key: a new receipt gets a fresh form, not the last one's edits. */}
          <ReviewForm
            key={receipt.id}
            nextHref={next ? `/receipts/${next.id}` : "/review"}
            receipt={{
              id: receipt.id,
              merchant: receipt.merchant,
              receipt_date: receipt.receipt_date,
              currency: receipt.currency,
              net_amount: receipt.net_amount,
              tax_amount: receipt.tax_amount,
              total_amount: receipt.total_amount,
              category: receipt.category,
            }}
          />
        </section>
      </div>
    </div>
  );
}
