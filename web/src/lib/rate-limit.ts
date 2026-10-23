import "server-only";

/**
 * Fixed-window, in-memory rate limiter.
 *
 * Good enough for local development and a single server process. It resets on restart
 * and is not shared between instances, so production deployments with more than one
 * instance (or serverless) should back this with a shared store such as Redis/Upstash,
 * keeping the same keys and limits.
 */
const windows = new Map<string, { count: number; resetAt: number }>();

export interface RateLimitRule {
  limit: number;
  windowMs: number;
}

export const LIMITS = {
  /** Failed-or-not sign-in attempts per username+IP. */
  signInPerAccount: { limit: 5, windowMs: 15 * 60_000 },
  /** All sign-in attempts per IP (slows credential stuffing across usernames). */
  signInPerIp: { limit: 30, windowMs: 15 * 60_000 },
  /** Registrations per IP. */
  registerPerIp: { limit: 5, windowMs: 60 * 60_000 },
} satisfies Record<string, RateLimitRule>;

/** Records one attempt and returns false if the key is over its limit. */
export function consume(key: string, rule: RateLimitRule, now = Date.now()): boolean {
  const current = windows.get(key);
  if (!current || current.resetAt <= now) {
    windows.set(key, { count: 1, resetAt: now + rule.windowMs });
    if (windows.size > 10_000) prune(now);
    return true;
  }
  current.count += 1;
  return current.count <= rule.limit;
}

export function reset(key: string) {
  windows.delete(key);
}

function prune(now: number) {
  for (const [key, entry] of windows) {
    if (entry.resetAt <= now) windows.delete(key);
  }
}

/** Client IP for rate-limit keys. Forwarded headers are only trusted behind a known proxy. */
export function clientIp(headers: Headers): string {
  if (process.env.TRUST_PROXY === "true") {
    const forwarded = headers.get("x-forwarded-for")?.split(",")[0]?.trim();
    if (forwarded) return forwarded;
  }
  return "direct";
}
