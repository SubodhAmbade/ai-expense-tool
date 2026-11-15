import { notFound } from "next/navigation";
import { Suspense } from "react";
import { API_URL, type Receipt } from "@/lib/api";
import ReviewForm from "./review-form";

export default function ReceiptPage(props: PageProps<"/receipts/[id]">) {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading receipt…</p>}>
      <ReceiptDetail params={props.params} />
    </Suspense>
  );
}

async function ReceiptDetail({ params }: { params: PageProps<"/receipts/[id]">["params"] }) {
  const { id } = await params;
  const res = await fetch(`${API_URL}/receipts/${encodeURIComponent(id)}`);
  if (res.status === 404 || res.status === 422) notFound();
  if (!res.ok) {
    return <p className="text-sm text-red-600">Couldn&apos;t load this receipt ({res.status}).</p>;
  }
  const receipt: Receipt = await res.json();

  return (
    <main className="grid gap-8 md:grid-cols-2">
      {/* A short-lived signed link from private storage, so next/image can't optimise it. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={receipt.image_url}
        alt="Receipt photo"
        className="max-h-[80vh] w-full rounded border object-contain"
      />
      <div className="flex flex-col gap-6">
        {receipt.status === "needs_review" ? (
          <div className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
            <p className="font-semibold">Needs review</p>
            <ul className="mt-2 list-disc pl-5">
              {receipt.validation_errors.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-green-700 dark:text-green-400">
            Confirmed. You can still correct it.
          </p>
        )}
        <ReviewForm
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
      </div>
    </main>
  );
}
