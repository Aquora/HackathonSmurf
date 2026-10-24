import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ObjectId } from "mongodb";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { PlayerProfileView } from "@/features/profile/PlayerProfileView";
import { countFriends } from "@/lib/friends";
import { getPlayerProfile } from "@/lib/profile";
import { getPlayerProgress, listQuests } from "@/lib/quests";

export const metadata: Metadata = { title: "Profile · Local Quest" };

export default async function ProfilePage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const session = await auth();
  if (!session?.user?.id) redirect("/sign-in?callbackUrl=/profile");

  const profile = await getPlayerProfile(session.user.id);
  if (!profile) redirect("/sign-in?callbackUrl=/profile");

  // Stats and badges are computed from the player's simulated check-ins.
  const userId = new ObjectId(session.user.id);
  const [progress, quests, friendsCount] = await Promise.all([getPlayerProgress(userId), listQuests(userId), countFriends(userId)]);

  return (
    <main className="profile-page">
      <PlayerProfileView profile={profile} progress={progress} quests={quests} friendsCount={friendsCount} mode="self" />
      <BottomNav active="/profile" />
    </main>
  );
}
