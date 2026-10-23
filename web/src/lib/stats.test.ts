import { MongoMemoryServer } from "mongodb-memory-server";
import { ObjectId, type Db } from "mongodb";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { getMongoClient } from "./db";
import { countFriends, getRelationship, pairKey, removeFriendship } from "./friends";
import { effectiveStreak, getPlayerStats, localDay } from "./stats";

let server: MongoMemoryServer;
let db: Db;
const alex = new ObjectId();
const sam = new ObjectId();
const jo = new ObjectId();

beforeAll(async () => {
  server = await MongoMemoryServer.create();
  // The app's shared client reads DATABASE_URL on first use.
  process.env.DATABASE_URL = `${server.getUri()}stats_test`;
  db = (await getMongoClient()).db();
}, 120_000);

afterAll(async () => {
  await (await getMongoClient()).close();
  await server?.stop();
});

beforeEach(async () => {
  await db.collection("friendships").deleteMany({});
  await db.collection("user_stats").deleteMany({});
});

async function befriend(a: ObjectId, b: ObjectId, status: "pending" | "accepted" = "accepted") {
  const { insertedId } = await db.collection("friendships").insertOne({
    requesterId: a,
    recipientId: b,
    pairKey: pairKey(a, b),
    status,
    createdAt: new Date(),
  });
  return insertedId.toHexString();
}

describe("relationships", () => {
  it("describes each side of a request and an accepted friendship", async () => {
    expect(await getRelationship(alex, alex)).toEqual({ kind: "self" });
    expect(await getRelationship(alex, sam)).toEqual({ kind: "none" });

    const requestId = await befriend(alex, sam, "pending");
    expect(await getRelationship(alex, sam)).toEqual({ kind: "outgoing", requestId });
    expect(await getRelationship(sam, alex)).toEqual({ kind: "incoming", requestId });

    await db.collection("friendships").updateOne({ pairKey: pairKey(alex, sam) }, { $set: { status: "accepted" } });
    expect(await getRelationship(sam, alex)).toEqual({ kind: "friends" });
  });

  it("counts only accepted friendships, in either direction", async () => {
    await befriend(alex, sam);
    await befriend(jo, alex);
    await befriend(sam, jo, "pending");
    expect(await countFriends(alex)).toBe(2);
    expect(await countFriends(sam)).toBe(1);
  });

  it("lets either friend remove the friendship, but not a stranger or a pending request", async () => {
    await befriend(alex, sam);
    await befriend(alex, jo, "pending");
    expect(await removeFriendship(jo, sam)).toBe(false);
    expect(await removeFriendship(jo, alex)).toBe(false); // still pending
    expect(await removeFriendship(sam, alex)).toBe(true);
    expect(await getRelationship(alex, sam)).toEqual({ kind: "none" });
  });
});

describe("player stats", () => {
  it("defaults to zero with no stats document", async () => {
    await befriend(alex, sam);
    expect(await getPlayerStats(alex)).toEqual({
      questsCompleted: 0,
      placesVisited: 0,
      dayStreak: 0,
      friendsCount: 1,
      earnedBadgeIds: [],
    });
  });

  it("reads stored counters and badges, ignoring unknown badge ids", async () => {
    const now = new Date("2026-10-23T20:00:00Z"); // Oct 23 in Los Angeles
    await db.collection("user_stats").insertOne({
      userId: sam,
      questsCompleted: 4,
      placesVisited: 11,
      currentStreakDays: 3,
      lastActiveDay: "2026-10-22",
      badges: [
        { id: "first_steps", earnedAt: now },
        { id: "made_up", earnedAt: now },
      ],
    });
    expect(await getPlayerStats(sam, now)).toEqual({
      questsCompleted: 4,
      placesVisited: 11,
      dayStreak: 3,
      friendsCount: 0,
      earnedBadgeIds: ["first_steps"],
    });
    // Two days later without activity, the streak has lapsed.
    expect((await getPlayerStats(sam, new Date("2026-10-25T20:00:00Z"))).dayStreak).toBe(0);
  });
});

describe("streak helpers", () => {
  it("counts a streak active today or yesterday only", () => {
    expect(effectiveStreak({ currentStreakDays: 5, lastActiveDay: "2026-10-23" }, "2026-10-23")).toBe(5);
    expect(effectiveStreak({ currentStreakDays: 5, lastActiveDay: "2026-10-22" }, "2026-10-23")).toBe(5);
    expect(effectiveStreak({ currentStreakDays: 5, lastActiveDay: "2026-10-21" }, "2026-10-23")).toBe(0);
    expect(effectiveStreak({ currentStreakDays: 0, lastActiveDay: null }, "2026-10-23")).toBe(0);
  });

  it("uses the Los Angeles calendar day", () => {
    expect(localDay(new Date("2026-10-24T05:00:00Z"))).toBe("2026-10-23");
    expect(localDay(new Date("2026-10-24T08:00:00Z"))).toBe("2026-10-24");
  });
});
