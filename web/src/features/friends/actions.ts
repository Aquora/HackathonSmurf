"use server";

import { revalidatePath } from "next/cache";
import { MongoServerError, ObjectId } from "mongodb";
import { z } from "zod";
import { auth } from "@/auth";
import {
  findPlayers,
  getFriendshipsCollection,
  getPlayerSummary,
  pairKey,
  removeFriendship,
  type PlayerSummary,
} from "@/lib/friends";
import { consume } from "@/lib/rate-limit";

export interface AddFriendState {
  error?: string;
  message?: string;
  /** Several players matched the name; the user picks one. */
  choices?: PlayerSummary[];
  /** Changes on every completed request so the popup can reset its input. */
  sentAt?: number;
}

const FRIEND_REQUESTS = { limit: 30, windowMs: 60 * 60_000 };
const querySchema = z.string().trim().min(1, "Enter a name or username.").max(60, "That's too long for a name or username.");

async function currentUserId(): Promise<ObjectId | null> {
  const id = (await auth())?.user?.id;
  return id && ObjectId.isValid(id) ? new ObjectId(id) : null;
}

function field(formData: FormData, name: string) {
  const value = formData.get(name);
  return typeof value === "string" ? value : "";
}

export async function sendFriendRequest(_previous: AddFriendState, formData: FormData): Promise<AddFriendState> {
  const userId = await currentUserId();
  if (!userId) return { error: "Your session has ended. Sign in again to add friends." };
  if (!consume(`friend-request:${userId.toHexString()}`, FRIEND_REQUESTS)) {
    return { error: "You've sent a lot of requests. Try again later." };
  }

  // Either a pick from an earlier list of matches, or a new name/username search.
  let target: PlayerSummary | null = null;
  const targetId = field(formData, "targetId");
  if (targetId) {
    if (ObjectId.isValid(targetId)) target = await getPlayerSummary(new ObjectId(targetId));
  } else {
    const parsed = querySchema.safeParse(field(formData, "query"));
    if (!parsed.success) return { error: parsed.error.issues[0].message };
    const matches = await findPlayers(parsed.data, userId);
    if (matches.length > 1) return { choices: matches, message: "More than one player matches. Who did you mean?" };
    target = matches[0] ?? null;
  }
  if (!target) return { error: "No player found with that name or username. Check the spelling and try again." };

  const targetObjectId = new ObjectId(target.id);
  if (targetObjectId.equals(userId)) return { error: "That's you! Try a friend's name or username." };

  const friendships = await getFriendshipsCollection();
  const key = pairKey(userId, targetObjectId);
  const existing = await friendships.findOne({ pairKey: key });
  const done = (message: string): AddFriendState => {
    revalidatePath("/friends", "layout");
    return { message, sentAt: Date.now() };
  };

  if (existing?.status === "accepted") return { message: `You're already friends with ${target.name}.`, sentAt: Date.now() };
  if (existing && existing.requesterId.equals(userId)) {
    return { message: `You already sent ${target.name} a request.`, sentAt: Date.now() };
  }
  if (existing) {
    // They already asked us: accept instead of creating a second request.
    await friendships.updateOne({ _id: existing._id, status: "pending" }, { $set: { status: "accepted", acceptedAt: new Date() } });
    return done(`${target.name} had already sent you a request. You're now friends!`);
  }

  try {
    await friendships.insertOne({
      _id: new ObjectId(),
      requesterId: userId,
      recipientId: targetObjectId,
      pairKey: key,
      status: "pending",
      createdAt: new Date(),
    });
  } catch (error) {
    // Both players sent a request at the same moment; the unique pair index kept just one.
    if (error instanceof MongoServerError && error.code === 11000) return done(`You and ${target.name} already have a request.`);
    throw error;
  }
  return done(`Friend request sent to ${target.name}.`);
}

export async function respondToFriendRequest(formData: FormData) {
  const userId = await currentUserId();
  const requestId = field(formData, "requestId");
  if (!userId || !ObjectId.isValid(requestId)) return;

  const friendships = await getFriendshipsCollection();
  // Only the recipient of a pending request can answer it.
  const filter = { _id: new ObjectId(requestId), recipientId: userId, status: "pending" as const };
  if (field(formData, "decision") === "accept") {
    await friendships.updateOne(filter, { $set: { status: "accepted", acceptedAt: new Date() } });
  } else {
    await friendships.deleteOne(filter);
  }
  revalidatePath("/friends", "layout");
}

export async function cancelFriendRequest(formData: FormData) {
  const userId = await currentUserId();
  const requestId = field(formData, "requestId");
  if (!userId || !ObjectId.isValid(requestId)) return;

  const friendships = await getFriendshipsCollection();
  // Only the sender of a pending request can cancel it.
  await friendships.deleteOne({ _id: new ObjectId(requestId), requesterId: userId, status: "pending" });
  revalidatePath("/friends", "layout");
}

export async function removeFriend(formData: FormData) {
  const userId = await currentUserId();
  const friendId = field(formData, "friendId");
  if (!userId || !ObjectId.isValid(friendId)) return;

  // Only an accepted friendship that includes the signed-in player is removed.
  await removeFriendship(userId, new ObjectId(friendId));
  revalidatePath("/friends", "layout");
  revalidatePath("/profile");
}
