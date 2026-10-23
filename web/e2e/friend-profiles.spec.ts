import { hash } from "@node-rs/argon2";
import { expect, test, type Browser, type Page } from "@playwright/test";
import { MongoClient, type ObjectId } from "mongodb";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("Set E2E_DATABASE_URL to the disposable database the app under test uses.");

const run = Date.now().toString(36);
const password = "walking2coffee";
const riley = { name: `Riley ${run}`, username: `riley_${run}` };
const casey = { name: `Casey ${run}`, username: `casey_${run}` };
const morgan = { name: `Morgan ${run}`, username: `morgan_${run}` };
const ids: Record<string, ObjectId> = {};

test.beforeAll(async () => {
  const mongo = await new MongoClient(databaseUrl).connect();
  const passwordHash = await hash(password, { memoryCost: 19456, timeCost: 2, parallelism: 1 });
  const users = mongo.db().collection("users");
  for (const u of [riley, casey, morgan]) {
    const { insertedId } = await users.insertOne({ ...u, email: `${u.username}@example.com`, passwordHash, createdAt: new Date() });
    ids[u.username] = insertedId;
  }
  // Casey finished one quest with three simulated check-ins: 3 places, 80 XP, "First steps".
  const stop = (n: number) => ({
    location: { name: `Demo Stop ${n}`, address: `${n} Example Ave`, closingTime: "22:00" },
    arrivalTime: "10:00",
    departureTime: "10:20",
    travelDistance: 1,
  });
  const now = new Date();
  await mongo
    .db()
    .collection("quests")
    .insertOne({
      userId: ids[casey.username],
      request: "coffee and art",
      route: {
        startLocation: { address: "1 Home St" },
        quests: [stop(1), stop(2), stop(3)],
        endLocation: { address: "1 Home St" },
        estimatedCost: 0,
        mock: true,
      },
      checkIns: [now, now, now],
      status: "done",
      mock: true,
      createdAt: now,
      completedAt: now,
    });
  await mongo.close();
});

async function signedInPage(browser: Browser, username: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await page.goto("/sign-in?callbackUrl=/friends");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL((url) => url.pathname === "/friends");
  return page;
}

const stat = (page: Page, label: string) => page.locator(".profile-stat", { hasText: label }).locator(".profile-stat__value");

test.describe.configure({ mode: "serial" });

test("friends see each other's stats; others only see a locked card", async ({ browser }) => {
  const rileyPage = await signedInPage(browser, riley.username);

  // Not friends yet: the card hides stats and offers "+ Add friend".
  await rileyPage.goto(`/friends/${ids[casey.username]}`);
  await expect(rileyPage.getByRole("heading", { name: `${casey.name}'s card` })).toBeVisible();
  await expect(rileyPage.getByText("Add them as a friend to see their stats and badges.")).toBeVisible();
  await expect(rileyPage.locator(".profile-stat")).toHaveCount(0);
  await rileyPage.getByRole("button", { name: `Add ${casey.name} as a friend` }).click();
  await expect(rileyPage.getByText("Friend request sent. You'll see their stats once they accept.")).toBeVisible();

  // Casey accepts from Riley's card.
  const caseyPage = await signedInPage(browser, casey.username);
  await caseyPage.getByRole("link", { name: new RegExp(riley.name) }).click();
  await expect(caseyPage).toHaveURL(new RegExp(`/friends/${ids[riley.username]}$`));
  await caseyPage.getByRole("button", { name: "Accept" }).click();
  await expect(caseyPage.getByText(/Joined .* · 1 friend$/)).toBeVisible();
  await expect(stat(caseyPage, "Quests done")).toHaveText("0");

  // Riley now sees Casey's real stats and earned badge.
  await rileyPage.reload();
  await expect(stat(rileyPage, "Quests done")).toHaveText("1");
  await expect(stat(rileyPage, "Places found")).toHaveText("3");
  await expect(stat(rileyPage, "Day streak")).toHaveText("1");
  await expect(rileyPage.getByText("80 XP")).toBeVisible();
  await expect(rileyPage.getByText("1/4")).toBeVisible();
  await expect(rileyPage.locator(".profile-badge--unlocked")).toHaveText(/First steps/);
  await expect(rileyPage.locator(".profile-badge--locked")).toHaveCount(3);

  // Own profile shows the friend count too.
  await rileyPage.goto("/profile");
  await expect(rileyPage.getByText(/· 1 friend$/)).toBeVisible();

  // Someone who isn't a friend still can't see Casey's stats.
  const morganPage = await signedInPage(browser, morgan.username);
  await morganPage.goto(`/friends/${ids[casey.username]}`);
  await expect(morganPage.locator(".profile-stat")).toHaveCount(0);
  await expect(morganPage.getByText(/^Joined /)).toBeVisible();
  await expect(morganPage.getByText(/^Joined .* · \d+ friends?$/)).toHaveCount(0);

  // Removing the friend locks the card again.
  await rileyPage.goto(`/friends/${ids[casey.username]}`);
  await rileyPage.getByRole("button", { name: `Remove ${casey.name} from friends` }).click();
  await expect(rileyPage.getByText("Add them as a friend to see their stats and badges.")).toBeVisible();
});

test("bad ids are not found and your own id goes to your profile", async ({ browser }) => {
  const page = await signedInPage(browser, morgan.username);
  expect((await page.goto("/friends/not-an-id"))?.status()).toBe(404);
  expect((await page.goto(`/friends/${"0".repeat(24)}`))?.status()).toBe(404);
  await page.goto(`/friends/${ids[morgan.username]}`);
  await expect(page).toHaveURL(/\/profile$/);
});
