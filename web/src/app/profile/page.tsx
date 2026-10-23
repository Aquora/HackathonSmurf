import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import lockKeyhole from "@/assets/lock-keyhole.svg";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { PlayerAvatar } from "@/components/PlayerAvatar/PlayerAvatar";
import { WideLink } from "@/components/WideButton/WideButton";
import { getPlayerProfile } from "@/lib/profile";
import "@/features/profile/profile.css";

export const metadata: Metadata = { title: "Profile · Local Quest" };

// Badges from the Figma frame. Quest progress isn't tracked yet, so every badge is locked
// and the stats start at zero instead of showing the design's sample numbers.
const BADGES = [
  { title: "First steps", milestone: "1st quest" },
  { title: "Hidden gem", milestone: "10 places" },
  { title: "On a roll", milestone: "7-day streak" },
  { title: "Town hero", milestone: "50 quests" },
];

const STATS = [
  { value: 0, label: "Quests done" },
  { value: 0, label: "Places found" },
  { value: 0, label: "Day streak" },
];

const joinedFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" });

export default async function ProfilePage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user?.id) redirect("/sign-in?callbackUrl=/profile");

  const profile = await getPlayerProfile(session.user.id);
  if (!profile) redirect("/sign-in?callbackUrl=/profile");

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
            <span className="profile-progress__level">LVL 1</span>
            <span>Local explorer</span>
          </div>
          <span className="profile-progress__xp">0 XP</span>
        </div>
        <div className="profile-progress__bar" role="progressbar" aria-label="Experience" aria-valuenow={0} aria-valuemin={0} aria-valuemax={100}>
          <div className="profile-progress__fill" style={{ width: "0%" }} />
        </div>
        <p className="profile-progress__hint">Complete quests to earn XP and level up.</p>
        <ul className="profile-stats">
          {STATS.map((stat) => (
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
          {BADGES.map((badge) => (
            <li key={badge.title} className="profile-badge profile-badge--locked">
              <span className="profile-badge__emblem">
                <Image src={lockKeyhole} alt="" />
              </span>
              <span className="profile-badge__title">{badge.title}</span>
              <span className="profile-badge__milestone">
                {badge.milestone}
                <span className="visually-hidden"> (locked)</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="profile-section profile-log" aria-labelledby="log-heading">
        <h2 className="profile-section__heading" id="log-heading">
          Quest log
        </h2>
        <p className="profile-log__empty">No quests completed yet. Finished quests will show up here.</p>
        <WideLink href="/quests" label="Find your next quest" />
      </section>

      <BottomNav active="/profile" />
    </main>
  );
}
