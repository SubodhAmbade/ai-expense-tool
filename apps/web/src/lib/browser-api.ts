import { createBrowserClient } from "@supabase/ssr";
import { API_URL, SUPABASE_KEY, SUPABASE_URL } from "./api";

// One client per browser tab (createBrowserClient reuses it); the session lives in cookies.
export const supabaseBrowser = () => createBrowserClient(SUPABASE_URL, SUPABASE_KEY);

// Call the API from the browser as the signed-in user. Network errors still throw, as fetch does.
// expectUser: refuse to send if another account signed in since (e.g. in another tab), checked on
// the same session read that supplies the token.
export async function apiFetch(path: string, init: RequestInit = {}, expectUser?: string): Promise<Response> {
  const auth = supabaseBrowser().auth;
  const session = (await auth.getSession()).data.session;
  if (expectUser && session?.user.id !== expectUser) {
    throw new Error("You're signed in as someone else now, so this was skipped.");
  }
  const token = session?.access_token ?? "";
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401) {
    // Refreshed while this request was in flight: still signed in, so just report the failure.
    if ((await auth.getSession()).data.session?.access_token !== token) return res;
    // Rejected by the API: end the session here too, or /login would bounce straight back.
    await auth.signOut({ scope: "local" });
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/login"); // a full page load, from code outside any component
  }
  return res;
}
