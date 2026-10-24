import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { ObjectId } from "mongodb";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { cancelFriendRequest, removeFriend, respondToFriendRequest } from "@/features/friends/actions";
import { AddFriendButton } from "@/features/friends/AddFriendButton";
import { PlayerProfileView } from "@/features/profile/PlayerProfileView";
import { countFriends, getRelationship, type Relationship } from "@/lib/friends";
import { getPlayerProfile } from "@/lib/profile";
import { getPlayerProgress, listQuests } from "@/lib/quests";
import "@/features/friends/friends.css";

export const metadata: Metadata = { title: "Player card · Local Quest" };

const LOCKED_MESSAGE: Record<"none" | "outgoing" | "incoming", string> = {
  none: "Add them as a friend to see their stats and badges.",
  outgoing: "Friend request sent. You'll see their stats once they accept.",
  incoming: "They want to be friends. Accept to see each other's stats.",
};

/**
 * Another player's card. Anyone signed in sees the banner; stats, badges, quest log, and
 * friend count are only shown to accepted friends.
 */
export default async function PlayerCardPage({ params }: { params: Promise<{ userId: string }> }) {
  const { userId } = await params;
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const viewerId = (await auth())?.user?.id;
  if (!viewerId || !ObjectId.isValid(viewerId)) redirect(`/sign-in?callbackUrl=/friends/${encodeURIComponent(userId)}`);
  if (!/^[a-f0-9]{24}$/i.test(userId)) notFound();
  if (userId.toLowerCase() === viewerId) redirect("/profile");

  const target = new ObjectId(userId);
  const [profile, relationship] = await Promise.all([getPlayerProfile(userId), getRelationship(new ObjectId(viewerId), target)]);
  if (!profile) notFound();

  const isFriend = relationship.kind === "friends";
  const [progress, quests, friendsCount] = isFriend
    ? await Promise.all([getPlayerProgress(target), listQuests(target), countFriends(target)])
    : [null, [], undefined];

  return (
    <main className="profile-page">
      <PlayerProfileView
        profile={profile}
        mode="friend"
        progress={progress}
        quests={quests}
        friendsCount={friendsCount}
        actions={<RelationshipActions relationship={relationship} playerId={userId} name={profile.displayName} />}
        lockedMessage={isFriend ? undefined : LOCKED_MESSAGE[relationship.kind as keyof typeof LOCKED_MESSAGE]}
      />
      <BottomNav active="/friends" />
    </main>
  );
}

function RelationshipActions({ relationship, playerId, name }: { relationship: Relationship; playerId: string; name: string }) {
  switch (relationship.kind) {
    case "none":
      return <AddFriendButton playerId={playerId} name={name} />;
    case "outgoing":
      return (
        <form action={cancelFriendRequest} className="friend-profile__action">
          <input type="hidden" name="requestId" value={relationship.requestId} />
          <button type="submit" className="small-button">
            Cancel request
          </button>
        </form>
      );
    case "incoming":
      return (
        <form action={respondToFriendRequest} className="friend-profile__action">
          <input type="hidden" name="requestId" value={relationship.requestId} />
          <button type="submit" name="decision" value="accept" className="small-button small-button--primary">
            Accept
          </button>
          <button type="submit" name="decision" value="decline" className="small-button">
            Decline
          </button>
        </form>
      );
    case "friends":
      return (
        <form action={removeFriend} className="friend-profile__action">
          <input type="hidden" name="friendId" value={playerId} />
          <button type="submit" className="small-button" aria-label={`Remove ${name} from friends`}>
            Remove friend
          </button>
        </form>
      );
    default:
      return null;
  }
}
