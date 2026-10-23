import { hash } from "@node-rs/argon2";
import { expect, test } from "@playwright/test";
import { MongoClient } from "mongodb";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("Set E2E_DATABASE_URL to the disposable database the app under test uses.");

test("quest board shows empty states and the filters switch sections", async ({ page }) => {
  const username = `board_${Date.now().toString(36)}`;
  const mongo = await new MongoClient(databaseUrl).connect();
  await mongo.db().collection("users").insertOne({
    name: "Jamie Park",
    username,
    email: `${username}@example.com`,
    emailVerified: null,
    passwordHash: await hash("walking2coffee", { memoryCost: 19456, timeCost: 2, parallelism: 1 }),
    createdAt: new Date(),
  });
  await mongo.close();

  await page.goto("/sign-in");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("walking2coffee");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/quests$/);

  await expect(page.getByText("Start a quest to begin your streak, Jamie!")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Keep exploring" })).toBeVisible();
  await expect(page.getByText("No quest in progress")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your next adventure" })).toBeVisible();

  await page.getByRole("button", { name: "In progress (0)" }).click();
  await expect(page.getByRole("button", { name: "In progress (0)" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { name: "Your next adventure" })).toHaveCount(0);

  await page.getByRole("button", { name: "Done (0)" }).click();
  await expect(page.getByText("No completed quests yet.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Keep exploring" })).toHaveCount(0);
});
