import { hash } from "@node-rs/argon2";
import { expect, test, type Browser, type Page } from "@playwright/test";
import { MongoClient } from "mongodb";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("Set E2E_DATABASE_URL to the disposable database the app under test uses.");

const run = Date.now().toString(36);
const password = "walking2coffee";
const alex = { name: "Alex Morgan", username: `alex_${run}` };
const sam = { name: "Sam Rivera", username: `sam_${run}` };
// Two different players who share a name (unique to this run).
const jordanName = `Jordan Lee ${run}`;
const jordans = [`jordan_a_${run}`, `jordan_b_${run}`];

test.beforeAll(async () => {
  const mongo = await new MongoClient(databaseUrl).connect();
  const passwordHash = await hash(password, { memoryCost: 19456, timeCost: 2, parallelism: 1 });
  const users = [alex, sam, ...jordans.map((username) => ({ name: jordanName, username }))];
  await mongo.db().collection("users").insertMany(
    users.map((u) => ({ ...u, email: `${u.username}@example.com`, emailVerified: null, passwordHash, createdAt: new Date() })),
  );
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

async function addFriend(page: Page, query: string) {
  const toggle = page.getByRole("button", { name: "+ Add friend" });
  const field = page.getByPlaceholder("Name or username");
  if ((await toggle.getAttribute("aria-expanded")) !== "true") {
    await toggle.click();
    await expect(field).toBeFocused(); // opening the popup focuses the search field
  } else {
    // React clears the form after each request; wait so the reset can't wipe the new text.
    await expect(field).toHaveValue("");
  }
  await field.fill(query);
  await page.getByRole("button", { name: "Add friend", exact: true }).click();
}

const popupStatus = (page: Page) => page.locator(".add-friend-popup__message");
const popupError = (page: Page) => page.locator(".add-friend-popup__error");

test.describe.configure({ mode: "serial" });

test("friends page requires sign-in", async ({ page }) => {
  await page.goto("/friends");
  await expect(page).toHaveURL(/\/sign-in\?callbackUrl=/);
});

test("send requests by username or name, then accept and cancel them", async ({ browser }) => {
  const alexPage = await signedInPage(browser, alex.username);
  await expect(alexPage.getByRole("heading", { name: "Your friends" })).toBeVisible();
  await expect(alexPage.getByText("No friends yet.")).toBeVisible();
  await expect(alexPage.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Friends" })).toHaveAttribute(
    "aria-current",
    "page",
  );

  // Escape closes the popup and returns focus to the button.
  await alexPage.getByRole("button", { name: "+ Add friend" }).click();
  await alexPage.keyboard.press("Escape");
  await expect(alexPage.getByRole("button", { name: "+ Add friend" })).toHaveAttribute("aria-expanded", "false");
  await expect(alexPage.getByRole("button", { name: "+ Add friend" })).toBeFocused();

  // By username, with "@".
  await addFriend(alexPage, `@${sam.username.toUpperCase()}`);
  await expect(popupStatus(alexPage)).toHaveText("Friend request sent to Sam Rivera.");
  await expect(alexPage.getByRole("heading", { name: "Sent requests" })).toBeVisible();

  // Sending again doesn't create a duplicate.
  await addFriend(alexPage, sam.username);
  await expect(popupStatus(alexPage)).toHaveText("You already sent Sam Rivera a request.");

  // Unknown players and yourself aren't found.
  await addFriend(alexPage, `nobody_${run}`);
  await expect(popupError(alexPage)).toHaveText(/No player found/);
  await addFriend(alexPage, alex.username);
  await expect(popupError(alexPage)).toHaveText(/No player found/);

  // By name: two players share it, so pick one.
  await addFriend(alexPage, jordanName.toLowerCase());
  await expect(popupStatus(alexPage)).toHaveText("More than one player matches. Who did you mean?");
  await alexPage.getByRole("button", { name: new RegExp(`@${jordans[1]}`) }).click();
  await expect(popupStatus(alexPage)).toHaveText(`Friend request sent to ${jordanName}.`);

  // Sam sees the request and accepts it.
  const samPage = await signedInPage(browser, sam.username);
  await expect(samPage.getByRole("heading", { name: "Friend requests" })).toBeVisible();
  await samPage.getByRole("button", { name: "Accept" }).click();
  await expect(samPage.getByRole("heading", { name: "Friend requests" })).toHaveCount(0);
  await expect(samPage.locator(".friend-row", { hasText: "Alex Morgan" })).toContainText("AM");

  // Alex now has Sam as a friend and can cancel the request to Jordan.
  await alexPage.reload();
  await expect(alexPage.locator(".friend-row", { hasText: "Sam Rivera" })).toContainText(`@${sam.username}`);
  const pendingJordan = alexPage.locator(".friend-row", { hasText: jordans[1] });
  await expect(pendingJordan).toContainText("Pending");
  await pendingJordan.getByRole("button", { name: "Cancel" }).click();
  await expect(alexPage.getByRole("heading", { name: "Sent requests" })).toHaveCount(0);

  // Already friends.
  await addFriend(alexPage, sam.username);
  await expect(popupStatus(alexPage)).toHaveText("You're already friends with Sam Rivera.");
});

test("clicking a friend opens their read-only player card; non-friends get a 404", async ({ browser }) => {
  const id = `card_${Date.now().toString(36)}`;
  const mongo = await new MongoClient(databaseUrl!).connect();
  const db = mongo.db();
  const passwordHash = await hash(password, { memoryCost: 19456, timeCost: 2, parallelism: 1 });
  const [viewer, friend, stranger] = await Promise.all(
    [
      { name: "Riley Brooks", username: `${id}_viewer` },
      { name: "Maya Chen", username: `${id}_friend` },
      { name: "Noah Williams", username: `${id}_stranger` },
    ].map(async (u) => {
      const { insertedId } = await db.collection("users").insertOne({
        ...u,
        email: `${u.username}@example.com`,
        emailVerified: null,
        passwordHash,
        createdAt: new Date("2026-06-15T12:00:00Z"),
      });
      return insertedId;
    }),
  );
  const key = [viewer.toHexString(), friend.toHexString()].sort().join(":");
  await db.collection("friendships").insertOne({
    requesterId: viewer,
    recipientId: friend,
    pairKey: key,
    status: "accepted",
    createdAt: new Date(),
    acceptedAt: new Date(),
  });
  // A finished quest for the friend, so their quest log has an entry.
  await db.collection("quests").insertOne({
    userId: friend,
    request: "coffee and art",
    route: {
      startLocation: { address: "1 Main St" },
      quests: [{ location: { name: "Demo Bean Coffee", address: "101 Example Ave", closingTime: "18:00" }, arrivalTime: "10:20", departureTime: "10:40", travelDistance: 1 }],
      endLocation: { address: "1 Main St" },
      estimatedCost: 5,
    },
    checkIns: [new Date()],
    status: "done",
    mock: true,
    createdAt: new Date(),
    completedAt: new Date(),
  });
  await mongo.close();

  const page = await signedInPage(browser, `${id}_viewer`);
  await page.locator(".friend-row__link", { hasText: "Maya Chen" }).click();
  await expect(page).toHaveURL((url) => url.pathname === `/friends/${friend.toHexString()}`);

  await expect(page.getByRole("heading", { name: "Player card" })).toBeVisible();
  await expect(page.locator(".player-banner__name")).toHaveText("Maya Chen");
  await expect(page.getByText(`@${id}_friend`)).toBeVisible();
  await expect(page.getByText("Joined June 2026")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Badge collection" })).toBeVisible();
  await expect(page.locator(".profile-log__item")).toHaveText("Demo Bean Coffee (demo)");
  // Read-only: no edit, no quest links, no next-quest button.
  await expect(page.getByRole("link", { name: "Edit profile" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Find your next quest" })).toHaveCount(0);
  await expect(page.locator(".profile-log a")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Friends" })).toHaveAttribute("aria-current", "page");

  await page.getByRole("link", { name: "← Back to friends" }).click();
  await expect(page).toHaveURL((url) => url.pathname === "/friends");

  // Not a friend, or no such player: same 404.
  for (const other of [stranger.toHexString(), "000000000000000000000000", "not-an-id"]) {
    const response = await page.goto(`/friends/${other}`);
    expect(response?.status()).toBe(404);
  }
  // Your own id goes to your own profile.
  await page.goto(`/friends/${viewer.toHexString()}`);
  await expect(page).toHaveURL((url) => url.pathname === "/profile");
});
