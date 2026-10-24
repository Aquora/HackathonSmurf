import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { ObjectId } from "mongodb";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { PlayerProfileView } from "@/features/profile/PlayerProfileView";
import { areFriends } from "@/lib/friends";
import { getPlayerProfile } from "@/lib/profile";
import { getPlayerProgress, listQuests } from "@/lib/quests";

export const metadata: Metadata = { title: "Friend's profile · Local Quest" };

/** A friend's read-only player card. Only accepted friends can see it. */
export default async function FriendProfilePage({ params }: { params: Promise<{ userId: string }> }) {
  const { userId: friendId } = await params;
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const viewerId = (await auth())?.user?.id;
  if (!viewerId || !ObjectId.isValid(viewerId)) redirect(`/sign-in?callbackUrl=/friends/${encodeURIComponent(friendId)}`);
  if (friendId === viewerId) redirect("/profile");
  if (!ObjectId.isValid(friendId)) notFound();

  const viewer = new ObjectId(viewerId);
  const friend = new ObjectId(friendId);
  // Same response for "not a friend" and "no such player", so ids can't be probed.
  if (!(await areFriends(viewer, friend))) notFound();

  const profile = await getPlayerProfile(friendId);
  if (!profile) notFound();
  const [progress, quests] = await Promise.all([getPlayerProgress(friend), listQuests(friend)]);

  return (
    <main className="profile-page">
      <PlayerProfileView profile={profile} progress={progress} quests={quests} mode="friend" />
      <BottomNav active="/friends" />
    </main>
  );
}
