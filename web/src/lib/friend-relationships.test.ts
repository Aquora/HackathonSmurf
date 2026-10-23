import { MongoMemoryServer } from "mongodb-memory-server";
import { ObjectId, type Db } from "mongodb";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { getMongoClient } from "./db";
import { countFriends, getRelationship, pairKey, removeFriendship } from "./friends";

let server: MongoMemoryServer;
let db: Db;
const alex = new ObjectId();
const sam = new ObjectId();
const jo = new ObjectId();

beforeAll(async () => {
  server = await MongoMemoryServer.create();
  // The app's shared client reads DATABASE_URL on first use.
  process.env.DATABASE_URL = `${server.getUri()}friends_test`;
  db = (await getMongoClient()).db();
}, 120_000);

afterAll(async () => {
  await (await getMongoClient()).close();
  await server?.stop();
});

beforeEach(async () => {
  await db.collection("friendships").deleteMany({});
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

describe("friend relationships", () => {
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
