export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// Public by design: the publishable key only lets people sign in; the database stays closed to it.
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";
export const IDLE_KEY = "lastActive"; // localStorage: when this browser was last used, shared by tabs

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
  note: string | null; // the reviewer's own note, at most 500 characters
  validation_errors: string[];
  image_url?: string;
};

export const label = (slug: string | null) => (slug ?? "").replace(/_/g, " ");
