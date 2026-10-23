import { hash } from "@node-rs/argon2";
import { expect, test, type Page } from "@playwright/test";
import { MongoClient } from "mongodb";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("Set E2E_DATABASE_URL to the disposable database the app under test uses.");

// 1x1 PNG.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);
const GOOGLE_PHOTO = "https://lh3.googleusercontent.com/a/e2e-test-photo=s96-c";

const run = Date.now().toString(36);
const password = "walking2coffee";

let mongo: MongoClient;
test.beforeAll(async () => {
  mongo = await new MongoClient(databaseUrl).connect();
});
test.afterAll(async () => {
  await mongo?.close();
});

async function createUser(username: string, extra: Record<string, unknown> = {}) {
  await mongo.db().collection("users").insertOne({
    name: username,
    username,
    email: `${username}@example.com`,
    emailVerified: null,
    passwordHash: await hash(password, { memoryCost: 19456, timeCost: 2, parallelism: 1 }),
    createdAt: new Date("2026-06-15T12:00:00Z"),
    ...extra,
  });
}

async function signIn(page: Page, username: string) {
  await page.goto("/sign-in?callbackUrl=/profile");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
}

const avatar = (page: Page) => page.locator(".player-banner__details .player-avatar");

test.describe.configure({ mode: "serial" });

test("profile requires sign-in, and the avatar route requires a session", async ({ page, request }) => {
  await page.goto("/profile");
  await expect(page).toHaveURL(/\/sign-in\?callbackUrl=/);
  expect((await request.get("/api/avatars/000000000000000000000000")).status()).toBe(401);
});

test("password account without a photo shows the default pixel explorer", async ({ page }) => {
  const username = `plain_${run}`;
  await createUser(username);
  await signIn(page, username);

  await expect(page.getByRole("heading", { name: "Your player card" })).toBeVisible();
  await expect(page.getByText(`@${username}`).first()).toBeVisible();
  await expect(page.getByText("Joined June 2026")).toBeVisible();
  await expect(avatar(page).locator(".player-avatar__explorer img")).toHaveCount(8);
  await expect(page.getByRole("link", { name: "Profile", exact: true })).toHaveAttribute("aria-current", "page");
});

test("account with a Google photo shows it by default", async ({ page }) => {
  const username = `google_${run}`;
  await createUser(username, { image: GOOGLE_PHOTO });
  await signIn(page, username);
  const img = avatar(page).locator("img.player-avatar__photo");
  await expect(img).toHaveAttribute("src", /googleusercontent\.com/);
});

test("uploaded picture replaces the Google photo, and removing it restores the photo", async ({ page }) => {
  const username = `google_${run}`;
  await signIn(page, username);

  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.locator('input[type="file"][name="avatar"]').setInputFiles({ name: "me.png", mimeType: "image/png", buffer: PNG });
  await page.getByRole("button", { name: "Save picture" }).click();

  const img = avatar(page).locator("img.player-avatar__photo");
  await expect(img).toHaveAttribute("src", /^\/api\/avatars\/[0-9a-f]{24}\?v=\d+$/);
  await expect(page.getByRole("button", { name: "Edit profile" })).toHaveAttribute("aria-expanded", "false");

  const response = await page.request.get((await img.getAttribute("src"))!);
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toBe("image/png");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(Buffer.from(await response.body()).equals(PNG)).toBe(true);

  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByRole("button", { name: /Remove uploaded picture \(use your Google photo\)/ }).click();
  await expect(avatar(page).locator("img.player-avatar__photo")).toHaveAttribute("src", /googleusercontent\.com/);
  const stored = await mongo.db().collection("users").findOne({ username });
  expect(stored?.avatarUpdatedAt).toBeUndefined();
});

test("files that aren't PNG, JPEG, or WebP are rejected on the server", async ({ page }) => {
  const username = `plain_${run}`;
  await signIn(page, username);
  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.locator('input[type="file"][name="avatar"]').setInputFiles({
    name: "evil.png",
    mimeType: "image/png",
    buffer: Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
  });
  await page.getByRole("button", { name: "Save picture" }).click();
  await expect(page.locator(".profile-editor__error")).toHaveText("Use a PNG, JPEG, or WebP image.");
  const user = await mongo.db().collection("users").findOne({ username });
  expect(await mongo.db().collection("avatars").countDocuments({ _id: user!._id })).toBe(0);
  expect(user?.avatarUpdatedAt).toBeUndefined();
});
