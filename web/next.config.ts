import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // web/ is its own package; don't let the empty lockfile at the repo root become the workspace root.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  // Native password-hashing module; load it from node_modules at runtime instead of bundling.
  serverExternalPackages: ["@node-rs/argon2"],
  poweredByHeader: false,
};

export default nextConfig;
