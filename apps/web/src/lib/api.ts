export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Keep in sync with CATEGORIES in apps/api/app/categorise.py (the API rejects anything else).
export const CATEGORIES = [
  "meals",
  "groceries",
  "office_supplies",
  "repairs_maintenance",
  "health",
  "transport",
  "travel",
  "accommodation",
  "software",
  "other",
];

export type Amount = string | number | null;

export type Receipt = {
  id: string;
  created_at: string;
  confirmed_at: string | null; // set when a person confirms; null when the checks accepted it
  status: "needs_review" | "confirmed";
  merchant: string | null;
  receipt_date: string | null;
  currency: string | null;
  net_amount: Amount;
  tax_amount: Amount;
  total_amount: Amount;
  category: string | null;
  validation_errors: string[];
  image_url?: string;
};

export const label = (slug: string | null) => (slug ?? "").replace(/_/g, " ");

// Newest first. Throws when the API is down so each page can say so in its own words.
export async function fetchReceipts(status?: Receipt["status"]): Promise<Receipt[]> {
  const res = await fetch(`${API_URL}/receipts${status ? `?status=${status}` : ""}`);
  if (!res.ok) throw new Error(`API returned ${res.status}`);
  return res.json();
}
