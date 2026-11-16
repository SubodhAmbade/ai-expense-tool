import { Suspense } from "react";
import { fetchReceipts, supabaseServer } from "@/lib/server-api";
import IdleSignOut from "./idle-sign-out";
import Sidebar from "./sidebar";
import SignOutButton from "./sign-out-button";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar
        queueCount={
          <Suspense fallback={null}>
            <QueueCount />
          </Suspense>
        }
        account={
          <Suspense fallback={null}>
            <Account />
          </Suspense>
        }
      />
      <main className="min-w-0 flex-1 px-5 py-8 md:px-10">{children}</main>
    </div>
  );
}

async function QueueCount() {
  const queue = await fetchReceipts("needs_review");
  if (!queue?.length) return null;
  return (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
      {queue.length}
    </span>
  );
}

async function Account() {
  const { data } = await (await supabaseServer()).auth.getClaims();
  return (
    <div className="flex items-center justify-between gap-2 border-t border-gray-200 px-5 py-3">
      <span className="truncate text-sm text-gray-600">{String(data?.claims.email ?? "")}</span>
      <SignOutButton />
      <IdleSignOut userId={String(data?.claims.sub ?? "")} />
    </div>
  );
}
