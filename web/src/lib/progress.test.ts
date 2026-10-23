import { describe, expect, it } from "vitest";
import { dayStreak, localDay, summarizeProgress } from "./progress";

// 2026-10-23 12:00 in Los Angeles (PDT, UTC-7).
const NOW = new Date("2026-10-23T19:00:00Z");
const daysAgo = (n: number) => new Date(NOW.getTime() - n * 24 * 60 * 60_000);

describe("dayStreak", () => {
  it("is 0 with no check-ins", () => {
    expect(dayStreak([], NOW)).toBe(0);
  });

  it("counts consecutive days ending today", () => {
    expect(dayStreak([NOW, daysAgo(1), daysAgo(2), daysAgo(4)], NOW)).toBe(3);
  });

  it("still counts a streak that ended yesterday", () => {
    expect(dayStreak([daysAgo(1), daysAgo(2)], NOW)).toBe(2);
  });

  it("is broken by a missed day", () => {
    expect(dayStreak([daysAgo(2), daysAgo(3)], NOW)).toBe(0);
  });

  it("uses Los Angeles days, not UTC days", () => {
    // 2026-10-24 03:00 UTC is still 2026-10-23 in Los Angeles.
    expect(localDay(new Date("2026-10-24T03:00:00Z"))).toBe("2026-10-23");
  });
});

describe("summarizeProgress", () => {
  it("starts at level 1 with everything locked", () => {
    const p = summarizeProgress({ questsDone: 0, checkIns: [] }, NOW);
    expect(p).toMatchObject({ xp: 0, level: 1, levelPercent: 0, placesFound: 0, dayStreak: 0 });
    expect(p.badges.every((b) => !b.unlocked)).toBe(true);
  });

  it("awards XP per check-in and per finished quest, and counts places once", () => {
    const checkIns = [
      { at: NOW, placeKey: "a" },
      { at: NOW, placeKey: "b" },
      { at: NOW, placeKey: "a" },
    ];
    const p = summarizeProgress({ questsDone: 1, checkIns }, NOW);
    expect(p.xp).toBe(3 * 10 + 50);
    expect(p.level).toBe(1);
    expect(p.levelPercent).toBe(80);
    expect(p.placesFound).toBe(2);
    expect(p.badges.find((b) => b.title === "First steps")?.unlocked).toBe(true);
  });

  it("levels up every 100 XP", () => {
    const checkIns = Array.from({ length: 6 }, (_, i) => ({ at: NOW, placeKey: String(i) }));
    const p = summarizeProgress({ questsDone: 2, checkIns }, NOW);
    expect(p.xp).toBe(160);
    expect(p).toMatchObject({ level: 2, levelPercent: 60 });
  });
});
