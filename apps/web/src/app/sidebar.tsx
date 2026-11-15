"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, Suspense, useState } from "react";

// Each icon is one SVG path (24×24 grid, stroked).
const NAV = [
  { href: "/", label: "Dashboard", icon: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" },
  { href: "/review", label: "Review queue", icon: "M9 11l3 3 8-8M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9" },
  { href: "/receipts", label: "All receipts", icon: "M4 6h16M4 12h16M4 18h10" },
  { href: "/export", label: "Export", icon: "M12 3v12M7 10l5 5 5-5M5 21h14" },
  { href: "/policy", label: "Policy", icon: "M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" },
];

export default function Sidebar({ queueCount }: { queueCount: ReactNode }) {
  const [open, setOpen] = useState(false); // the menu on phone-width screens
  const nav = { open, close: () => setOpen(false), queueCount };

  return (
    <aside className="border-b border-gray-200 bg-white md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0 md:border-r md:border-b-0">
      <div className="flex items-center justify-between px-5 py-3 md:py-6">
        <Link href="/" className="flex items-center gap-2.5 font-semibold">
          <span aria-hidden className="flex size-8 items-center justify-center rounded-lg bg-blue-700 text-white">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" />
            </svg>
          </span>
          Expense Tool
        </Link>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls="main-nav"
          aria-label="Menu"
          className="flex size-11 items-center justify-center rounded-lg text-gray-700 hover:bg-gray-100 md:hidden"
        >
          <svg aria-hidden width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
      {/* Reading the URL waits for the request, so the links first show without the highlight. */}
      <Suspense fallback={<Nav pathname="" {...nav} />}>
        <CurrentNav {...nav} />
      </Suspense>
    </aside>
  );
}

type NavProps = { open: boolean; close: () => void; queueCount: ReactNode };

function CurrentNav(props: NavProps) {
  return <Nav pathname={usePathname()} {...props} />;
}

function Nav({ pathname, open, close, queueCount }: NavProps & { pathname: string }) {
  return (
    <nav id="main-nav" aria-label="Main" className={`${open ? "flex" : "hidden"} flex-col gap-1 px-3 pb-4 md:flex`}>
      {NAV.map((item) => {
        const on = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={close}
            aria-current={on ? "page" : undefined}
            className={`flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm ${
              on ? "bg-blue-50 font-semibold text-blue-900" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d={item.icon} />
            </svg>
            <span className="flex-1">{item.label}</span>
            {item.href === "/review" && queueCount}
            {item.href === "/policy" && <span className="text-xs text-gray-500">Soon</span>}
          </Link>
        );
      })}
    </nav>
  );
}
