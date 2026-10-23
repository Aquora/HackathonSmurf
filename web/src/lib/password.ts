import "server-only";
import { hash, verify } from "@node-rs/argon2";

// Argon2id with OWASP-recommended minimums (19 MiB memory, 2 iterations, 1 lane).
// @node-rs/argon2 defaults to Argon2id; the parameters are pinned so they can't drift.
const ARGON2_OPTIONS = { memoryCost: 19456, timeCost: 2, parallelism: 1 } as const;

export function hashPassword(password: string): Promise<string> {
  return hash(password, ARGON2_OPTIONS);
}

// A real hash of a random value, verified when the username doesn't exist so that
// "no such user" and "wrong password" take about the same time.
let dummyHash: Promise<string> | undefined;
function getDummyHash() {
  dummyHash ??= hash(crypto.randomUUID(), ARGON2_OPTIONS);
  return dummyHash;
}

/** Constant-time comparison of a submitted password against a stored Argon2 hash. */
export async function verifyPassword(storedHash: string | undefined, password: string): Promise<boolean> {
  if (!storedHash) {
    await verify(await getDummyHash(), password).catch(() => false);
    return false;
  }
  try {
    return await verify(storedHash, password);
  } catch {
    return false;
  }
}
