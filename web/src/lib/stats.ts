import "server-only";
import { ObjectId, type Collection } from "mongodb";
import { getMongoClient } from "./db";
import { countFriends } from "./friends";

/**
 * Player activity shown on profiles. One `user_stats` document per player; nothing writes
 * it yet, so every counter reads as zero until quest completion is recorded.
 */
export interface UserStatsDocument {
  userId: ObjectId;
  questsCompleted: number;
  placesVisited: number;
  currentStreakDays: number;
  /** Last day with activity, "YYYY-MM-DD" in STATS_TIMEZONE. */
  lastActiveDay: string | null;
  /** Ids from BADGES. */
  badges: { id: string; earnedAt: Date }[];
}

export interface PlayerStats {
  questsCompleted: number;
  placesVisited: number;
  dayStreak: number;
  friendsCount: number;
  earnedBadgeIds: string[];
}

/** Badge collection from the profile Figma frame. */
export const BADGES = [
  { id: "first_steps", title: "First steps", milestone: "1st quest" },
  { id: "hidden_gem", title: "Hidden gem", milestone: "10 places" },
  { id: "on_a_roll", title: "On a roll", milestone: "7-day streak" },
  { id: "town_hero", title: "Town hero", milestone: "50 quests" },
] as const;

export const STATS_TIMEZONE = "America/Los_Angeles";

let indexes: Promise<unknown> | undefined;

export async function getStatsCollection(): Promise<Collection<UserStatsDocument>> {
  const collection = (await getMongoClient()).db().collection<UserStatsDocument>("user_stats");
  indexes ??= collection.createIndex({ userId: 1 }, { unique: true, name: "user_stats_user_unique" }).catch((error) => {
    indexes = undefined;
    throw error;
  });
  await indexes;
  return collection;
}

/** "YYYY-MM-DD" for `date` in `timeZone`. */
export function localDay(date: Date, timeZone = STATS_TIMEZONE): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
}

/** A streak only counts if the last activity was today or yesterday; otherwise it has lapsed to 0. */
export function effectiveStreak(
  stored: Pick<UserStatsDocument, "currentStreakDays" | "lastActiveDay">,
  today: string,
): number {
  if (!stored.lastActiveDay || stored.currentStreakDays <= 0) return 0;
  const days = (Date.parse(`${today}T00:00:00Z`) - Date.parse(`${stored.lastActiveDay}T00:00:00Z`)) / 86_400_000;
  return days === 0 || days === 1 ? stored.currentStreakDays : 0;
}

export async function getPlayerStats(userId: ObjectId, now = new Date()): Promise<PlayerStats> {
  const [stored, friendsCount] = await Promise.all([
    (await getStatsCollection()).findOne({ userId }),
    countFriends(userId),
  ]);
  const known = new Set<string>(BADGES.map((badge) => badge.id));
  return {
    questsCompleted: stored?.questsCompleted ?? 0,
    placesVisited: stored?.placesVisited ?? 0,
    dayStreak: stored ? effectiveStreak(stored, localDay(now)) : 0,
    friendsCount,
    earnedBadgeIds: (stored?.badges ?? []).map((badge) => badge.id).filter((id) => known.has(id)),
  };
}
