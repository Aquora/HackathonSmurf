"use server";

import { revalidatePath } from "next/cache";
import { Binary, ObjectId } from "mongodb";
import { auth } from "@/auth";
import { getAvatarsCollection, getUsersCollection } from "@/lib/db";
import { MAX_AVATAR_BYTES, sniffImageType } from "@/lib/image-type";
import { consume } from "@/lib/rate-limit";

export interface AvatarFormState {
  error?: string;
  /** Increments on each success so the client can close the editor. */
  savedAt?: number;
}

const AVATAR_CHANGES = { limit: 10, windowMs: 60 * 60_000 };

async function requireUserId(): Promise<ObjectId | null> {
  const session = await auth();
  const id = session?.user?.id;
  return id && ObjectId.isValid(id) ? new ObjectId(id) : null;
}

export async function uploadAvatar(_previous: AvatarFormState, formData: FormData): Promise<AvatarFormState> {
  // Authenticate inside the action; rendering the form only to signed-in users is not a boundary.
  const userId = await requireUserId();
  if (!userId) return { error: "Your session has ended. Sign in again to change your picture." };

  const file = formData.get("avatar");
  if (!(file instanceof File) || file.size === 0) return { error: "Choose an image to upload." };
  if (file.size > MAX_AVATAR_BYTES) return { error: "That image is too large. Use one under 2 MB." };

  if (!consume(`avatar:${userId.toHexString()}`, AVATAR_CHANGES)) {
    return { error: "Too many picture changes. Try again later." };
  }

  const bytes = new Uint8Array(await file.arrayBuffer());
  const contentType = sniffImageType(bytes);
  if (!contentType) return { error: "Use a PNG, JPEG, or WebP image." };

  const updatedAt = new Date();
  const avatars = await getAvatarsCollection();
  await avatars.replaceOne(
    { _id: userId },
    { data: new Binary(bytes), contentType, size: bytes.length, updatedAt },
    { upsert: true },
  );
  const users = await getUsersCollection();
  await users.updateOne({ _id: userId }, { $set: { avatarUpdatedAt: updatedAt } });

  revalidatePath("/profile");
  revalidatePath("/settings");
  return { savedAt: updatedAt.getTime() };
}

export async function removeAvatar(): Promise<AvatarFormState> {
  const userId = await requireUserId();
  if (!userId) return { error: "Your session has ended. Sign in again to change your picture." };

  const avatars = await getAvatarsCollection();
  await avatars.deleteOne({ _id: userId });
  const users = await getUsersCollection();
  await users.updateOne({ _id: userId }, { $unset: { avatarUpdatedAt: "" } });

  revalidatePath("/profile");
  revalidatePath("/settings");
  return { savedAt: Date.now() };
}
