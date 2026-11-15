import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import { fetchReceipts } from "@/lib/api";
import Sidebar from "./sidebar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Expense Tool",
  description: "Receipt photos to accounting-ready expense data",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
      <body className="font-sans">
        <div className="flex min-h-screen flex-col md:flex-row">
          <Sidebar
            queueCount={
              <Suspense fallback={null}>
                <QueueCount />
              </Suspense>
            }
          />
          <main className="min-w-0 flex-1 px-5 py-8 md:px-10">{children}</main>
        </div>
      </body>
    </html>
  );
}

async function QueueCount() {
  const queue = await fetchReceipts("needs_review").catch(() => []);
  if (queue.length === 0) return null;
  return (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
      {queue.length}
    </span>
  );
}
