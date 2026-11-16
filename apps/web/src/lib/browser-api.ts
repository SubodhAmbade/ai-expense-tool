import { createBrowserClient } from "@supabase/ssr";
import { API_URL, SUPABASE_KEY, SUPABASE_URL } from "./api";

// One client per browser tab (createBrowserClient reuses it); the session lives in cookies.
export const supabaseBrowser = () => createBrowserClient(SUPABASE_URL, SUPABASE_KEY);

// Call the API from the browser as the signed-in user. Network errors still throw, as fetch does.
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { data } = await supabaseBrowser().auth.getSession();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${data.session?.access_token ?? ""}`);
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  // Signed out or expired: a full page load to /login, from code outside any component.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  if (res.status === 401) window.location.assign("/login");
  return res;
}
