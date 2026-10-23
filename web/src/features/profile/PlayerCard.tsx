import type { ReactNode } from "react";
import Image from "next/image";
import lockKeyhole from "@/assets/lock-keyhole.svg";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import type { PlayerProfile } from "@/lib/profile";
import { BADGES, type PlayerStats } from "@/lib/stats";
import "./profile.css";

const joinedFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" });

interface PlayerBannerProps {
  profile: PlayerProfile;
  heading: string;
  /** Shown next to "Joined …" when the viewer may see stats. */
  friendsCount?: number;
  children?: ReactNode;
}

/** Banner from the profile Figma frame: avatar, name, handle, joined date, then a row of actions. */
export function PlayerBanner({ profile, heading, friendsCount, children }: PlayerBannerProps) {
  return (
    <section className="player-banner" aria-labelledby="player-card-heading">
      <div className="player-banner__inner">
        <h1 className="player-banner__heading" id="player-card-heading">
          {heading}
        </h1>
        <div className="player-banner__details">
          <PlayerAvatar avatar={profile.avatar} name={profile.displayName} />
          <div className="player-banner__identity">
            <p className="player-banner__name">{profile.displayName}</p>
            {profile.username && <p className="player-banner__handle">@{profile.username}</p>}
            <p className="player-banner__meta">
              Joined {joinedFormat.format(profile.joinedAt)}
              {friendsCount !== undefined && (
                <>
                  {" · "}
                  {friendsCount} {friendsCount === 1 ? "friend" : "friends"}
                </>
              )}
            </p>
          </div>
        </div>
        {children && <div className="player-banner__tagline-row">{children}</div>}
      </div>
      <div className="player-banner__ground" />
    </section>
  );
}

/** Progress, stats, and badge collection. XP and levels aren't tracked yet, so they start at level 1. */
export function PlayerStatsSections({ stats }: { stats: PlayerStats }) {
  const earned = new Set(stats.earnedBadgeIds);
  const statItems = [
    { value: stats.questsCompleted, label: "Quests done" },
    { value: stats.placesVisited, label: "Places found" },
    { value: stats.dayStreak, label: "Day streak" },
  ];

  return (
    <>
      <section className="profile-section profile-progress" aria-label="Progress">
        <div className="profile-progress__summary">
          <div className="profile-progress__rank">
            <span className="profile-progress__level">LVL 1</span>
            <span>Local explorer</span>
          </div>
          <span className="profile-progress__xp">0 XP</span>
        </div>
        <div
          className="profile-progress__bar"
          role="progressbar"
          aria-label="Experience"
          aria-valuenow={0}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className="profile-progress__fill" style={{ width: "0%" }} />
        </div>
        <p className="profile-progress__hint">Complete quests to earn XP and level up.</p>
        <ul className="profile-stats">
          {statItems.map((stat) => (
            <li key={stat.label} className="profile-stat">
              <span className="profile-stat__value">{stat.value}</span>
              <span className="profile-stat__label">{stat.label}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="profile-section profile-badges" aria-labelledby="badges-heading">
        <h2 className="profile-section__heading" id="badges-heading">
          Badge collection{" "}
          <span className="profile-badges__count">
            {earned.size}/{BADGES.length}
          </span>
        </h2>
        <ul className="profile-badges__list">
          {BADGES.map((badge) => {
            const locked = !earned.has(badge.id);
            return (
              <li key={badge.id} className={`profile-badge${locked ? " profile-badge--locked" : ""}`}>
                <span className="profile-badge__emblem">{locked && <Image src={lockKeyhole} alt="" />}</span>
                <span className="profile-badge__title">{badge.title}</span>
                <span className="profile-badge__milestone">
                  {badge.milestone}
                  <span className="visually-hidden">{locked ? " (locked)" : " (earned)"}</span>
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </>
  );
}
