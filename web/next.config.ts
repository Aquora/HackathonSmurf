import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // web/ is its own package; don't let the empty lockfile at the repo root become the workspace root.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  // Native password-hashing module; load it from node_modules at runtime instead of bundling.
  serverExternalPackages: ["@node-rs/argon2"],
  poweredByHeader: false,
  // Self-contained server in .next/standalone for the Docker image (see web/Dockerfile).
  // Vercel builds its own output, so standalone is only used off Vercel.
  output: process.env.VERCEL ? undefined : "standalone",
  experimental: {
    // Profile pictures are uploaded through a server action (2 MB file limit plus form overhead).
    serverActions: { bodySizeLimit: "3mb" },
  },
  // The Explore page was removed; the quest board is the signed-in home page.
  async redirects() {
    return [{ source: "/explore", destination: "/quests", permanent: false }];
  },
  images: {
    // Google account profile photos.
    remotePatterns: [{ protocol: "https", hostname: "*.googleusercontent.com", pathname: "/**" }],
  },
};

export default nextConfig;
