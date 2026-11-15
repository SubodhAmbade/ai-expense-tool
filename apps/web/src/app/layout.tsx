import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
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
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">
        <nav className="flex gap-6 border-b border-zinc-200 px-6 py-4 text-sm dark:border-zinc-800">
          <span className="font-semibold">AI Expense Tool</span>
          <Link href="/">Upload</Link>
          <Link href="/receipts?status=needs_review">Review queue</Link>
          <Link href="/receipts">All receipts</Link>
        </nav>
        <div className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">{children}</div>
      </body>
    </html>
  );
}
