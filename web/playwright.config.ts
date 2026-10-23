import { defineConfig } from "@playwright/test";

// Runs against an already-running app (npm run dev) whose DATABASE_URL points at a
// disposable test database. E2E_DATABASE_URL must be that same database; the suite
// inserts and inspects users there. Never point it at real data.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    channel: process.env.E2E_BROWSER_CHANNEL ?? "chrome",
    trace: "retain-on-failure",
  },
});
