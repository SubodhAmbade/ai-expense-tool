import Link from "next/link";
import { label, type Receipt } from "@/lib/api";

// The one receipts table, shared by the dashboard, the review queue and All receipts.
export default function ReceiptTable({ receipts }: { receipts: Receipt[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="text-xs tracking-wide text-gray-500 uppercase">
          <tr>
            <th scope="col" className="px-5 py-2.5 font-medium">Merchant</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Date</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Category</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Total</th>
            <th scope="col" className="px-5 py-2.5 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {receipts.map((r) => (
            <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-5 py-3 font-medium">
                <Link href={`/receipts/${r.id}`} className="hover:underline">
                  {r.merchant ?? "Unknown merchant"}
                </Link>
              </td>
              <td className="px-3 py-3 whitespace-nowrap text-gray-600">{r.receipt_date ?? "—"}</td>
              <td className="px-3 py-3 text-gray-600 capitalize">{label(r.category)}</td>
              <td className="px-3 py-3 text-right whitespace-nowrap tabular-nums">
                {r.total_amount ?? "—"} <span className="text-gray-500">{r.currency ?? ""}</span>
              </td>
              <td className="px-5 py-3">
                {r.status === "confirmed" ? (
                  <span className="text-green-700">Confirmed</span>
                ) : (
                  <span className="inline-block max-w-64 truncate rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                    {r.validation_errors[0] ?? "Needs review"}
                    {r.validation_errors.length > 1 && ` +${r.validation_errors.length - 1}`}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
