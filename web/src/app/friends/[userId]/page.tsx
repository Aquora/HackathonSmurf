import type { Metadata } from "next";
import Link from "next/link";
import { ObjectId } from "mongodb";
import { notFound, redirect } from "next/navigation";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { AddFriendButton } from "@/features/friends/AddFriendButton";
import { cancelFriendRequest, removeFriend, respondToFriendRequest } from "@/features/friends/actions";
import { PlayerBanner, PlayerStatsSections } from "@/features/profile/PlayerCard";
import { countFriends, getRelationship, type Relationship } from "@/lib/friends";
import { getPlayerProfile } from "@/lib/profile";
import { getPlayerProgress } from "@/lib/quests";
import "@/features/friends/friends.css";
import "@/features/profile/profile.css";

export const metadata: Metadata = { title: "Player card · Local Quest" };

const LOCKED_MESSAGE: Record<"none" | "outgoing" | "incoming", string> = {
  none: "Add them as a friend to see their stats and badges.",
  outgoing: "Friend request sent. You'll see their stats once they accept.",
  incoming: "They want to be friends. Accept to see each other's stats.",
};

/** Another player's card. Stats and badges are only shown to accepted friends. */
export default async function PlayerCardPage(props: PageProps<"/friends/[userId]">) {
  const { userId } = await props.params;
  const viewerId = (await auth())?.user?.id;
  if (!viewerId || !ObjectId.isValid(viewerId)) redirect(`/sign-in?callbackUrl=/friends/${encodeURIComponent(userId)}`);
  if (!/^[a-f0-9]{24}$/i.test(userId)) notFound();
  if (userId.toLowerCase() === viewerId) redirect("/profile");

  const target = new ObjectId(userId);
  const [profile, relationship] = await Promise.all([
    getPlayerProfile(userId),
    getRelationship(new ObjectId(viewerId), target),
  ]);
  if (!profile) notFound();
  // Stats, badges, and friend count are for accepted friends only.
  const stats =
    relationship.kind === "friends"
      ? await Promise.all([getPlayerProgress(target), countFriends(target)]).then(([progress, friendsCount]) => ({
          progress,
          friendsCount,
        }))
      : null;

  return (
    <main className="profile-page">
      <PlayerBanner profile={profile} heading={`${profile.displayName}'s card`} friendsCount={stats?.friendsCount}>
        <Link className="friend-profile__back" href="/friends">
          ← Friends
        </Link>
        <RelationshipActions relationship={relationship} playerId={userId} name={profile.displayName} />
      </PlayerBanner>

      {stats ? (
        <PlayerStatsSections progress={stats.progress} />
      ) : (
        <section className="profile-section" aria-label="Stats">
          <p className="friend-profile__locked">
            {LOCKED_MESSAGE[relationship.kind as keyof typeof LOCKED_MESSAGE]}
          </p>
        </section>
      )}

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
