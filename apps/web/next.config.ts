import type { NextConfig } from "next";

// On Vercel, refuse to build without the three public settings: a missing or empty one doesn't
// fail on its own, it just sends requests to the wrong place. They're baked in at build time.
if (process.env.VERCEL) {
  const problems = [];
  for (const name of ["NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]) {
    if (!process.env[name]?.trim()) problems.push(`${name} is missing or empty`);
  }
  const api = process.env.NEXT_PUBLIC_API_URL?.trim() ?? "";
  console.log(`Building with NEXT_PUBLIC_API_URL="${api}"`); // public value, safe to log
  if (api && !/^https:\/\/[^/]+$/.test(api)) {
    problems.push(`NEXT_PUBLIC_API_URL must be just the API's address, like https://name.onrender.com (got "${api}")`);
  }
  if (problems.length) throw new Error(`Vercel environment variables:\n- ${problems.join("\n- ")}`);
}

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
