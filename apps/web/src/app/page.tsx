import { Suspense } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function ApiStatus() {
  let status: string;
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    status = res.ok ? ((await res.json()) as { status: string }).status : `error (${res.status})`;
  } catch {
    status = "unreachable";
  }
  return <span className={status === "ok" ? "text-green-600" : "text-red-600"}>{status}</span>;
}

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold tracking-tight">AI Expense Tool</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Receipt photos in, structured and categorised expense data out.
      </p>
      <p className="font-mono text-sm">
        API:{" "}
        <Suspense fallback={<span className="text-zinc-500">checking…</span>}>
          <ApiStatus />
        </Suspense>
      </p>
    </main>
  );
}
