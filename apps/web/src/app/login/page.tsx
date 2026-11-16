import { Suspense } from "react";
import LoginForm from "./login-form";

export default function LoginPage(props: PageProps<"/login">) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <section className="flex flex-col justify-between gap-10 bg-gray-900 px-8 py-10 text-gray-100 md:w-[42%] md:px-14 md:py-14">
        <div className="flex items-center gap-2.5 font-semibold">
          <span aria-hidden className="flex size-8 items-center justify-center rounded-lg bg-blue-700">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" />
            </svg>
          </span>
          Expense Tool
        </div>
        <div className="flex flex-col gap-4">
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Receipts in, clean expense data out.</h1>
          <p className="max-w-md text-gray-300">
            The numbers are checked by plain code. Anything unclear waits for you to confirm it.
          </p>
        </div>
        <p className="text-sm text-gray-400">Prototype · accounts are created by the owner</p>
      </section>
      <main className="flex flex-1 items-center justify-center bg-white px-6 py-12">
        <Suspense fallback={null}>
          <Form searchParams={props.searchParams} />
        </Suspense>
      </main>
    </div>
  );
}

async function Form({ searchParams }: { searchParams: PageProps<"/login">["searchParams"] }) {
  const { reason, next } = await searchParams;
  return <LoginForm idle={reason === "idle"} next={sameSite(next)} />;
}

const BASE = "http://app.invalid"; // any fixed origin: only "does it stay on it" matters

const OFF_SITE = /^\/[\\/]/; // "//evil.com" and "/\evil.com" are other sites, not paths

// The path to return to after sign-in, only if it stays on this site; otherwise "/". Browsers drop
// tabs and newlines from URLs ("/\t/evil.com" becomes "//evil.com"), so control characters are
// refused; parsing can also produce an off-site path ("/..//evil.com" becomes "//evil.com"), so
// the parsed result is checked again.
function sameSite(next: string | string[] | undefined): string {
  if (typeof next !== "string" || !next.startsWith("/") || OFF_SITE.test(next) || /[\u0000-\u001f\u007f]/.test(next)) {
    return "/";
  }
  const url = new URL(next, BASE);
  const path = url.pathname + url.search + url.hash;
  return url.origin === BASE && !OFF_SITE.test(path) ? path : "/";
}
