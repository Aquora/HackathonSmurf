import type { Metadata } from "next";
import Link from "next/link";
import { ObjectId } from "mongodb";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { WideLink } from "@/components/WideButton/WideButton";
import { PlayerBanner, PlayerStatsSections } from "@/features/profile/PlayerCard";
import { getPlayerProfile } from "@/lib/profile";
import { getPlayerStats } from "@/lib/stats";
import "@/features/profile/profile.css";

export const metadata: Metadata = { title: "Profile · Local Quest" };

export default async function ProfilePage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user?.id) redirect("/sign-in?callbackUrl=/profile");

  const profile = await getPlayerProfile(session.user.id);
  if (!profile) redirect("/sign-in?callbackUrl=/profile");
  const stats = await getPlayerStats(new ObjectId(session.user.id));

  return (
    <main className="profile-page">
      <PlayerBanner profile={profile} heading="Your player card" friendsCount={stats.friendsCount}>
        <p className="player-banner__tagline">Finding little adventures.</p>
        <Link className="profile-edit-button" href="/settings">
          Edit profile
        </Link>
      </PlayerBanner>

      <PlayerStatsSections stats={stats} />

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
