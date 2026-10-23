import { hash } from "@node-rs/argon2";
import { expect, test, type Page } from "@playwright/test";
import { MongoClient } from "mongodb";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("Set E2E_DATABASE_URL to the disposable database the app under test uses.");

const run = Date.now().toString(36);
const player = { username: `player_${run}`, email: `player_${run}@example.com`, password: "walking2coffee" };
const GENERIC_ERROR = "That username and password don't match. Try again.";
// Next.js renders its own empty role="alert" route announcer, so target the form alert.
const formAlert = (page: Page) => page.locator(".auth-form__alert");

let mongo: MongoClient;
test.beforeAll(async () => {
  mongo = await new MongoClient(databaseUrl).connect();
});
test.afterAll(async () => {
  await mongo?.close();
});
const users = () => mongo.db().collection("users");

async function signInWithPassword(page: Page, username: string, password: string) {
  await page.goto("/sign-in");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

test.describe.configure({ mode: "serial" });

test("protected route redirects signed-out visitors to sign-in", async ({ page }) => {
  await page.goto("/explore");
  await expect(page).toHaveURL(/\/sign-in\?callbackUrl=/);
  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
});

test("registration rejects weak passwords on the server", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Username").fill(`weak_${run}`);
  await page.getByLabel("Email").fill(`weak_${run}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("short");
  await page.getByRole("button", { name: "Sign up" }).click();
  await expect(page.getByText("Use 10–128 characters, with at least one letter and one number.").first()).toBeVisible();
  expect(await users().countDocuments({ username: `weak_${run}` })).toBe(0);
});

test("new username/password registration signs in and stores only a hash", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Username").fill(player.username.toUpperCase());
  await page.getByLabel("Email").fill(player.email);
  await page.getByLabel("Password", { exact: true }).fill(player.password);
  await page.getByRole("button", { name: "Sign up" }).click();

  await expect(page).toHaveURL(/\/explore$/);
  await expect(page.getByText(`@${player.username}`)).toBeVisible();

  const stored = await users().findOne({ username: player.username });
  expect(stored?.email).toBe(player.email);
  expect(stored?.passwordHash).toMatch(/^\$argon2id\$/);
  expect(JSON.stringify(stored)).not.toContain(player.password);
});

test("session cookie is httpOnly, persistent, and the session payload has no secrets", async ({ page, context }) => {
  await signInWithPassword(page, player.username, player.password);
  await expect(page).toHaveURL(/\/explore$/);

  const cookie = (await context.cookies()).find((c) => c.name.endsWith("authjs.session-token"));
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  const days = ((cookie?.expires ?? 0) * 1000 - Date.now()) / 86_400_000;
  expect(days).toBeGreaterThan(29);

  const session = await (await page.request.get("/api/auth/session")).json();
  expect(session.user.username).toBe(player.username);
  expect(JSON.stringify(session)).not.toMatch(/passwordHash|argon2/);

  // Still signed in after closing and reopening the page.
  await page.close();
  const again = await context.newPage();
  await again.goto("/explore");
  await expect(again.getByText(`@${player.username}`)).toBeVisible();
});

test("duplicate usernames and emails are rejected with a generic message", async ({ page }) => {
  for (const [username, email] of [
    [player.username, `other_${run}@example.com`],
    [`other_${run}`, player.email.toUpperCase()],
  ]) {
    await page.goto("/register");
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill("another2password");
    await page.getByRole("button", { name: "Sign up" }).click();
    await expect(formAlert(page)).toHaveText(/couldn't create an account with that username or email/);
  }
  expect(await users().countDocuments({ email: player.email })).toBe(1);
});

test("sign out ends the session and protects pages again", async ({ page }) => {
  await signInWithPassword(page, player.username, player.password);
  await expect(page).toHaveURL(/\/explore$/);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/explore");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("username/password sign-in goes to Explore", async ({ page }) => {
  await signInWithPassword(page, player.username, player.password);
  await expect(page).toHaveURL(/\/explore$/);
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
});

test("wrong password and unknown username get the same generic error", async ({ page }) => {
  await signInWithPassword(page, player.username, "wrong2password");
  await expect(formAlert(page)).toHaveText(GENERIC_ERROR);
  await expect(page).toHaveURL(/\/sign-in/);

  await signInWithPassword(page, `nobody_${run}`, "wrong2password");
  await expect(formAlert(page)).toHaveText(GENERIC_ERROR);
});

test("existing user created before this auth flow can sign in", async ({ page }) => {
  // Simulates a pre-existing account record (inserted directly, not through registration).
  const existing = { username: `legacy_${run}`, password: "old2account!" };
  await users().insertOne({
    name: "Legacy Player",
    username: existing.username,
    email: `legacy_${run}@example.com`,
    emailVerified: null,
    passwordHash: await hash(existing.password, { memoryCost: 19456, timeCost: 2, parallelism: 1 }),
    createdAt: new Date("2026-01-01"),
  });
  await signInWithPassword(page, existing.username, existing.password);
  await expect(page).toHaveURL(/\/explore$/);
  await expect(page.getByText(`@${existing.username}`)).toBeVisible();
});

test("repeated failed sign-ins are rate limited", async ({ page }) => {
  const target = `limited_${run}`;
  for (let attempt = 0; attempt < 5; attempt++) {
    await signInWithPassword(page, target, "wrong2password");
    await expect(formAlert(page)).toHaveText(GENERIC_ERROR);
  }
  await signInWithPassword(page, target, "wrong2password");
  await expect(formAlert(page)).toHaveText(/Too many attempts/);
});

test("Continue with Google starts OAuth with the configured callback URL", async ({ page, baseURL }) => {
  let authorizeUrl: URL | undefined;
  await page.route("https://accounts.google.com/**", async (route) => {
    authorizeUrl = new URL(route.request().url());
    await route.fulfill({ status: 200, body: "stubbed Google consent screen" });
  });
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Continue with Google" }).click();
  await expect.poll(() => authorizeUrl?.toString()).toBeTruthy();

  expect(authorizeUrl!.pathname).toMatch(/\/o\/oauth2\/v2\/auth$|\/o\/oauth2\/auth$/);
  expect(authorizeUrl!.searchParams.get("redirect_uri")).toBe(`${baseURL}/api/auth/callback/google`);
  expect(authorizeUrl!.searchParams.get("client_id")).toBe(process.env.E2E_GOOGLE_CLIENT_ID);
  expect(authorizeUrl!.searchParams.get("scope")).toContain("email");
});

test("Google sign-in for an email owned by a password account explains what to do", async ({ page }) => {
  await page.goto("/sign-in?error=OAuthAccountNotLinked");
  await expect(formAlert(page)).toContainText("Sign in with your username and password instead");
});
