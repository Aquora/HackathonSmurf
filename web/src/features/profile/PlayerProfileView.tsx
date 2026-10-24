import Image from "next/image";
import Link from "next/link";
import lockKeyhole from "@/assets/lock-keyhole.svg";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import { WideLink } from "@/components/WideButton/WideButton";
import type { PlayerProfile } from "@/lib/profile";
import type { PlayerProgress } from "@/lib/progress";
import type { QuestView } from "@/lib/quests";
import "./profile.css";

const joinedFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" });

interface PlayerProfileViewProps {
  profile: PlayerProfile;
  progress: PlayerProgress;
  quests: QuestView[];
  /** "self" is your own card; "friend" is read-only (no edit, no quest links, no next-quest button). */
  mode: "self" | "friend";
}

/** Player card from the "LocalQuest player profile" frame, for your own profile or a friend's. */
export function PlayerProfileView({ profile, progress, quests, mode }: PlayerProfileViewProps) {
  const self = mode === "self";
  const finished = quests.filter((q) => q.status === "done");
  const stats = [
    { value: progress.questsDone, label: "Quests done" },
    { value: progress.placesFound, label: "Places found" },
    { value: progress.dayStreak, label: "Day streak" },
  ];

  return (
    <>
      <section className="player-banner" aria-labelledby="player-card-heading">
        <div className="player-banner__inner">
          {!self && (
            <Link className="player-banner__back" href="/friends">
              ← Back to friends
            </Link>
          )}
          <h1 className="player-banner__heading" id="player-card-heading">
            {self ? "Your player card" : "Player card"}
          </h1>
          <div className="player-banner__details">
            <PlayerAvatar avatar={profile.avatar} name={profile.displayName} />
            <div className="player-banner__identity">
              <p className="player-banner__name">{profile.displayName}</p>
              {profile.username && <p className="player-banner__handle">@{profile.username}</p>}
              <p className="player-banner__meta">Joined {joinedFormat.format(profile.joinedAt)}</p>
            </div>
          </div>
          <div className="player-banner__tagline-row">
            <p className="player-banner__tagline">Finding little adventures.</p>
            {self && (
              <Link className="profile-edit-button" href="/settings">
                Edit profile
              </Link>
            )}
          </div>
        </div>
        <div className="player-banner__ground" />
      </section>

      <section className="profile-section profile-progress" aria-label="Progress">
        <div className="profile-progress__summary">
          <div className="profile-progress__rank">
            <span className="profile-progress__level">LVL {progress.level}</span>
            <span>Local explorer</span>
          </div>
          <span className="profile-progress__xp">{progress.xp} XP</span>
        </div>
        <div className="profile-progress__bar" role="progressbar" aria-label="Experience" aria-valuenow={progress.levelPercent} aria-valuemin={0} aria-valuemax={100}>
          <div className="profile-progress__fill" style={{ width: `${progress.levelPercent}%` }} />
        </div>
        {self && <p className="profile-progress__hint">Complete quests to earn XP and level up.</p>}
        <ul className="profile-stats">
          {stats.map((stat) => (
            <li key={stat.label} className="profile-stat">
              <span className="profile-stat__value">{stat.value}</span>
              <span className="profile-stat__label">{stat.label}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="profile-section profile-badges" aria-labelledby="badges-heading">
        <h2 className="profile-section__heading" id="badges-heading">
          Badge collection
        </h2>
        <ul className="profile-badges__list">
          {progress.badges.map((badge) => (
            <li key={badge.title} className={`profile-badge${badge.unlocked ? " profile-badge--unlocked" : " profile-badge--locked"}`}>
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

      <section className="profile-section profile-log" aria-labelledby="log-heading">
        <h2 className="profile-section__heading" id="log-heading">
          Quest log
        </h2>
        {finished.length === 0 ? (
          <p className="profile-log__empty">
            {self ? "No quests completed yet. Finished quests will show up here." : "No quests completed yet."}
          </p>
        ) : (
          <ul className="profile-log__list">
            {finished.slice(0, 10).map((quest) => {
              const label = `${quest.route.quests.map((stop) => stop.location.name).join(" → ")}${quest.mock ? " (demo)" : ""}`;
              return (
                <li key={quest.id}>
                  {/* Quest detail pages are private to their owner, so a friend's log isn't linked. */}
                  {self ? (
                    <Link className="profile-log__item" href={`/quests/${quest.id}`}>
                      {label}
                    </Link>
                  ) : (
                    <span className="profile-log__item">{label}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {self && <WideLink href="/quests" label="Find your next quest" />}
      </section>
    </>
  );
}
