import type { ReactNode } from "react";
import Image from "next/image";
import lockKeyhole from "@/assets/lock-keyhole.svg";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import type { PlayerProfile } from "@/lib/profile";
import type { PlayerProgress } from "@/lib/progress";
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

/** Progress, stats, and badge collection, computed from the player's simulated check-ins. */
export function PlayerStatsSections({ progress }: { progress: PlayerProgress }) {
  const unlocked = progress.badges.filter((badge) => badge.unlocked).length;
  const statItems = [
    { value: progress.questsDone, label: "Quests done" },
    { value: progress.placesFound, label: "Places found" },
    { value: progress.dayStreak, label: "Day streak" },
  ];

  return (
    <>
      <section className="profile-section profile-progress" aria-label="Progress">
        <div className="profile-progress__summary">
          <div className="profile-progress__rank">
            <span className="profile-progress__level">LVL {progress.level}</span>
            <span>Local explorer</span>
          </div>
          <span className="profile-progress__xp">{progress.xp} XP</span>
        </div>
        <div
          className="profile-progress__bar"
          role="progressbar"
          aria-label="Experience"
          aria-valuenow={progress.levelPercent}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className="profile-progress__fill" style={{ width: `${progress.levelPercent}%` }} />
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
            {unlocked}/{progress.badges.length}
          </span>
        </h2>
        <ul className="profile-badges__list">
          {progress.badges.map((badge) => (
            <li
              key={badge.title}
              className={`profile-badge${badge.unlocked ? " profile-badge--unlocked" : " profile-badge--locked"}`}
            >
              <span className="profile-badge__emblem">
                {badge.unlocked ? <span aria-hidden="true">★</span> : <Image src={lockKeyhole} alt="" />}
              </span>
              <span className="profile-badge__title">{badge.title}</span>
              <span className="profile-badge__milestone">
                {badge.milestone}
                <span className="visually-hidden">{badge.unlocked ? " (unlocked)" : " (locked)"}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
