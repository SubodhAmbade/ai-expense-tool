import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { API_URL, type Receipt, SUPABASE_KEY, SUPABASE_URL } from "./api";

// Server components only: reads the sign-in cookie. Cookies can't be written while a page
// renders, so setAll is a no-op here; proxy.ts refreshes the session before every page.
export async function supabaseServer() {
  await connection(); // checking a token's expiry reads the clock: do it per request, not at build
  const store = await cookies();
  return createServerClient(SUPABASE_URL, SUPABASE_KEY, {
    cookies: { getAll: () => store.getAll(), setAll: () => {} },
  });
}

// GET from the API as the signed-in user. null = the API couldn't be reached. A rejected
// sign-in goes back to the login page (outside any try, so the redirect isn't swallowed).
export async function apiGet(path: string): Promise<Response | null> {
  const { data } = await (await supabaseServer()).auth.getSession(); // the API verifies the token
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${data.session?.access_token ?? ""}` },
    });
  } catch {
    return null;
  }
  if (res.status === 401) redirect("/login");
  return res;
}

// Newest first; null when the API is down or errors, so each page can say so in its own words.
export async function fetchReceipts(status?: Receipt["status"]): Promise<Receipt[] | null> {
  const res = await apiGet(`/receipts${status ? `?status=${status}` : ""}`);
  return res?.ok ? res.json() : null;
}
