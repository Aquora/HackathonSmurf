import { describe, expect, it } from "vitest";
import { safeRedirectPath } from "@/features/auth/redirects";
import { hashPassword, verifyPassword } from "./password";
import { consume } from "./rate-limit";
import { registrationSchema, signInSchema } from "./validation";

const valid = { username: "Jamie_Quests", email: " Jamie@Example.com ", password: "walking2coffee" };

describe("registration validation", () => {
  it("normalizes username and email to lowercase", () => {
    const result = registrationSchema.parse(valid);
    expect(result.username).toBe("jamie_quests");
    expect(result.email).toBe("jamie@example.com");
  });

  it.each([
    ["too short", "ab"],
    ["too long", "a".repeat(21)],
    ["bad characters", "jamie quests!"],
  ])("rejects usernames that are %s", (_, username) => {
    expect(registrationSchema.safeParse({ ...valid, username }).success).toBe(false);
  });

  it("rejects invalid emails", () => {
    expect(registrationSchema.safeParse({ ...valid, email: "not-an-email" }).success).toBe(false);
  });

  it.each([
    ["shorter than 10 characters", "short1abc"],
    ["missing a number", "onlyletterspassword"],
    ["missing a letter", "12345678901"],
    ["longer than 128 characters", `a1${"x".repeat(127)}`],
    ["containing the username", "jamie_quests123"],
    ["containing the email name", "xxjamie12345"],
  ])("rejects passwords %s", (_, password) => {
    expect(registrationSchema.safeParse({ ...valid, password }).success).toBe(false);
  });

  it("keeps sign-in validation shape-only", () => {
    expect(signInSchema.safeParse({ username: "Anyone", password: "x" }).success).toBe(true);
    expect(signInSchema.safeParse({ username: "", password: "x" }).success).toBe(false);
  });
});

describe("password hashing", () => {
  it("stores an Argon2id hash, never the password", async () => {
    const stored = await hashPassword("walking2coffee");
    expect(stored).toMatch(/^\$argon2id\$v=19\$m=19456,t=2,p=1\$/);
    expect(stored).not.toContain("walking2coffee");
  });

  it("verifies only the matching password", async () => {
    const stored = await hashPassword("walking2coffee");
    expect(await verifyPassword(stored, "walking2coffee")).toBe(true);
    expect(await verifyPassword(stored, "walking2coffeE")).toBe(false);
  });

  it("returns false for missing or malformed hashes", async () => {
    expect(await verifyPassword(undefined, "anything123")).toBe(false);
    expect(await verifyPassword("not-a-hash", "anything123")).toBe(false);
  });
});

describe("rate limiting", () => {
  it("allows up to the limit per window, then blocks until it resets", () => {
    const rule = { limit: 3, windowMs: 1000 };
    const key = `test-${Math.random()}`;
    expect([1, 2, 3].map(() => consume(key, rule, 0))).toEqual([true, true, true]);
    expect(consume(key, rule, 999)).toBe(false);
    expect(consume(key, rule, 1000)).toBe(true);
  });
});

describe("post-sign-in redirects", () => {
  it.each([
    [undefined, "/quests"],
    ["/quests", "/quests"],
    ["/profile?tab=badges", "/profile?tab=badges"],
    ["https://evil.example", "/quests"],
    ["//evil.example", "/quests"],
    ["/\\evil.example", "/quests"],
    ["http://localhost:3000/profile?x=1", "/profile?x=1"],
    ["http://evil.example/profile", "/quests"],
    ["javascript:alert(1)", "/quests"],
  ])("maps %s to %s", (input, expected) => {
    expect(safeRedirectPath(input, "localhost:3000")).toBe(expected);
  });
});
