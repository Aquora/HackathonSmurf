/** XP, level, streak and badges from a player's simulated check-ins. Pure, so it is unit-tested. */

export const XP_PER_CHECK_IN = 10;
export const XP_PER_QUEST = 50;
export const XP_PER_LEVEL = 100;
/** Streak days are counted in the quest area's local time, not the server's. */
export const PROGRESS_TIMEZONE = "America/Los_Angeles";

export interface CheckIn {
  at: Date;
  /** Identifies a place so repeat visits count once toward "places found". */
  placeKey: string;
}

export interface Badge {
  /** Stable key, e.g. for picking the badge's picture. */
  id: string;
  title: string;
  milestone: string;
  unlocked: boolean;
}

export interface PlayerProgress {
  xp: number;
  level: number;
  /** 0–100: progress toward the next level. */
  levelPercent: number;
  questsDone: number;
  placesFound: number;
  dayStreak: number;
  badges: Badge[];
}

const dayFormat = new Intl.DateTimeFormat("en-CA", { timeZone: PROGRESS_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" });

/** "YYYY-MM-DD" in the progress time zone. */
export function localDay(date: Date): string {
  return dayFormat.format(date);
}

function previousDay(day: string): string {
  const d = new Date(`${day}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

/** Consecutive days with at least one check-in, ending today (or yesterday, if today has none yet). */
export function dayStreak(checkInDates: Date[], now: Date): number {
  const days = new Set(checkInDates.map(localDay));
  let day = localDay(now);
  if (!days.has(day)) day = previousDay(day);
  let streak = 0;
  while (days.has(day)) {
    streak += 1;
    day = previousDay(day);
  }
  return streak;
}

export function summarizeProgress(input: { questsDone: number; checkIns: CheckIn[] }, now: Date): PlayerProgress {
  const xp = input.checkIns.length * XP_PER_CHECK_IN + input.questsDone * XP_PER_QUEST;
  const placesFound = new Set(input.checkIns.map((c) => c.placeKey)).size;
  const streak = dayStreak(
    input.checkIns.map((c) => c.at),
    now,
  );
  return {
    xp,
    level: Math.floor(xp / XP_PER_LEVEL) + 1,
    levelPercent: Math.round(((xp % XP_PER_LEVEL) / XP_PER_LEVEL) * 100),
    questsDone: input.questsDone,
    placesFound,
    dayStreak: streak,
    badges: [
      // Earned by creating an account, so every player has it.
      { id: "new-beginning", title: "A new beginning", milestone: "At Cal Poly Pomona", unlocked: true },
      { id: "first-steps", title: "First steps", milestone: "1st quest", unlocked: input.questsDone >= 1 },
      { id: "hidden-gem", title: "Hidden gem", milestone: "10 places", unlocked: placesFound >= 10 },
      { id: "on-a-roll", title: "On a roll", milestone: "7-day streak", unlocked: streak >= 7 },
      { id: "town-hero", title: "Town hero", milestone: "50 quests", unlocked: input.questsDone >= 50 },
    ],
  };
}
