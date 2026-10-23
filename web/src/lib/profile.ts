import "server-only";
import { ObjectId } from "mongodb";
import { getUsersCollection } from "./db";

export type AvatarSource =
  | { kind: "upload"; src: string }
  | { kind: "google"; src: string }
  | { kind: "default" };

export interface PlayerProfile {
  displayName: string;
  username: string | null;
  joinedAt: Date;
  avatar: AvatarSource;
  /** True when a Google photo exists, even if an uploaded picture currently takes priority. */
  hasGooglePhoto: boolean;
}

/** Google profile photos are served from *.googleusercontent.com (allowed in next.config.ts). */
function isGooglePhoto(url: string) {
  try {
    const { protocol, hostname } = new URL(url);
    return protocol === "https:" && (hostname === "googleusercontent.com" || hostname.endsWith(".googleusercontent.com"));
  } catch {
    return false;
  }
}

export function avatarUrl(userId: string, updatedAt: Date) {
  return `/api/avatars/${userId}?v=${updatedAt.getTime()}`;
}

/** Profile fields the UI may see. Never includes the password hash or email. */
export async function getPlayerProfile(userId: string): Promise<PlayerProfile | null> {
  if (!ObjectId.isValid(userId)) return null;
  const _id = new ObjectId(userId);
  const users = await getUsersCollection();
  const user = await users.findOne(
    { _id },
    { projection: { name: 1, username: 1, image: 1, createdAt: 1, avatarUpdatedAt: 1 } },
  );
  if (!user) return null;

  // Priority: uploaded picture, then the Google account photo, then the default pixel explorer.
  const googlePhoto = user.image && isGooglePhoto(user.image) ? user.image : null;
  const avatar: AvatarSource = user.avatarUpdatedAt
    ? { kind: "upload", src: avatarUrl(userId, user.avatarUpdatedAt) }
    : googlePhoto
      ? { kind: "google", src: googlePhoto }
      : { kind: "default" };

  return {
    displayName: user.name || user.username || "Explorer",
    username: user.username ?? null,
    // Accounts created through Google have no createdAt; the ObjectId records creation time.
    joinedAt: user.createdAt ?? _id.getTimestamp(),
    avatar,
    hasGooglePhoto: googlePhoto !== null,
  };
}
