import type { Metadata } from "next";
import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { ObjectId } from "mongodb";
import { auth } from "@/auth";
import { BottomNav } from "@/components/BottomNav/BottomNav";
import { cancelFriendRequest, respondToFriendRequest } from "@/features/friends/actions";
import { AddFriendPopup } from "@/features/friends/AddFriendPopup";
import { getFriendsOverview, initials, type PlayerSummary } from "@/lib/friends";
import "@/features/friends/friends.css";

export const metadata: Metadata = { title: "Friends · Local Quest" };

function PlayerRow({ player, children }: { player: PlayerSummary; children?: ReactNode }) {
  return (
    <li className="friend-row">
      <span className="friend-row__avatar" aria-hidden="true">
        {initials(player.name)}
      </span>
      <span className="friend-row__identity">
        <span className="friend-row__name">{player.name}</span>
        {player.username && <span className="friend-row__handle">@{player.username}</span>}
      </span>
      {children && <span className="friend-row__actions">{children}</span>}
    </li>
  );
}

/** "LocalQuest friends" Figma frame (2021:139), plus pending requests. */
export default async function FriendsPage() {
  // The proxy already redirects signed-out visitors; this check covers anything it misses.
  const userId = (await auth())?.user?.id;
  if (!userId || !ObjectId.isValid(userId)) redirect("/sign-in?callbackUrl=/friends");

  const { friends, incoming, outgoing } = await getFriendsOverview(new ObjectId(userId));

  return (
    <main className="friends-page">
      <section className="friends-banner" aria-labelledby="friends-heading">
        <div className="friends-banner__inner">
          <h1 className="friends-banner__heading" id="friends-heading">
            Your friends
          </h1>
          <AddFriendPopup />
        </div>
        <div className="friends-banner__ground" />
      </section>

      <div className="friends-content">
        {incoming.length > 0 && (
          <section aria-labelledby="incoming-heading">
            <h2 className="friends-section__heading" id="incoming-heading">
              Friend requests
            </h2>
            <ul className="friend-list">
              {incoming.map((player) => (
                <PlayerRow key={player.requestId} player={player}>
                  <form action={respondToFriendRequest}>
                    <input type="hidden" name="requestId" value={player.requestId} />
                    <button type="submit" name="decision" value="accept" className="small-button small-button--primary">
                      Accept
                    </button>
                  </form>
                  <form action={respondToFriendRequest}>
                    <input type="hidden" name="requestId" value={player.requestId} />
                    <button type="submit" name="decision" value="decline" className="small-button">
                      Decline
                    </button>
                  </form>
                </PlayerRow>
              ))}
            </ul>
          </section>
        )}

        <section aria-labelledby="friends-list-heading">
          <h2 className="visually-hidden" id="friends-list-heading">
            Friends
          </h2>
          {friends.length > 0 ? (
            <ul className="friend-list">
              {friends.map((player) => (
                <PlayerRow key={player.id} player={player} />
              ))}
            </ul>
          ) : (
            <p className="friends-empty">No friends yet. Tap “+ Add friend” to send your first request.</p>
          )}
        </section>

        {outgoing.length > 0 && (
          <section aria-labelledby="outgoing-heading">
            <h2 className="friends-section__heading" id="outgoing-heading">
              Sent requests
            </h2>
            <ul className="friend-list">
              {outgoing.map((player) => (
                <PlayerRow key={player.requestId} player={player}>
                  <span className="friend-row__pending">Pending</span>
                  <form action={cancelFriendRequest}>
                    <input type="hidden" name="requestId" value={player.requestId} />
                    <button type="submit" className="small-button">
                      Cancel
                    </button>
                  </form>
                </PlayerRow>
              ))}
            </ul>
          </section>
        )}
      </div>

      <BottomNav active="/friends" />
    </main>
  );
}
