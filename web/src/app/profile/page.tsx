import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import lockKeyhole from "@/assets/lock-keyhole.svg";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import { WideLink } from "@/components/WideButton/WideButton";
import { ObjectId } from "mongodb";
import { getPlayerProfile } from "@/lib/profile";
import { getPlayerProgress, listQuests } from "@/lib/quests";
import "@/features/profile/profile.css";

export const metadata: Metadata = { title: "Profile · Local Quest" };

const joinedFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" });

export default async function ProfilePage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user?.id) redirect("/sign-in?callbackUrl=/profile");

  const profile = await getPlayerProfile(session.user.id);
  if (!profile) redirect("/sign-in?callbackUrl=/profile");

  // Badges and stats from the Figma frame, computed from the player's simulated check-ins.
  const userId = new ObjectId(session.user.id);
  const [progress, quests] = await Promise.all([getPlayerProgress(userId), listQuests(userId)]);
  const finished = quests.filter((q) => q.status === "done");
  const stats = [
    { value: progress.questsDone, label: "Quests done" },
    { value: progress.placesFound, label: "Places found" },
    { value: progress.dayStreak, label: "Day streak" },
  ];

  return (
    <main className="profile-page">
      <section className="player-banner" aria-labelledby="player-card-heading">
        <div className="player-banner__inner">
          <h1 className="player-banner__heading" id="player-card-heading">
            Your player card
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
            <Link className="profile-edit-button" href="/settings">
              Edit profile
            </Link>
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
        <p className="profile-progress__hint">Complete quests to earn XP and level up.</p>
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
          <p className="profile-log__empty">No quests completed yet. Finished quests will show up here.</p>
        ) : (
          <ul className="profile-log__list">
            {finished.slice(0, 10).map((quest) => (
              <li key={quest.id}>
                <Link className="profile-log__item" href={`/quests/${quest.id}`}>
                  {quest.route.quests.map((stop) => stop.location.name).join(" → ")}
                  {quest.mock && " (demo)"}
                </Link>
              </li>
            ))}
          </ul>
        )}
        <WideLink href="/quests" label="Find your next quest" />
      </section>

      <BottomNav active="/profile" />
    </main>
  );
}
