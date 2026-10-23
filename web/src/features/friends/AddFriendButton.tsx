"use client";

import { useActionState } from "react";
import { sendFriendRequest, type AddFriendState } from "./actions";

/** Sends a request to one known player (from their profile), reusing the popup's server action. */
export function AddFriendButton({ playerId, name }: { playerId: string; name: string }) {
  const [state, formAction, pending] = useActionState<AddFriendState, FormData>(sendFriendRequest, {});

  return (
    <form action={formAction} className="friend-profile__action">
      <input type="hidden" name="targetId" value={playerId} />
      <button type="submit" className="profile-edit-button" disabled={pending} aria-label={`Add ${name} as a friend`}>
        {pending ? "Sending…" : "+ Add friend"}
      </button>
      {state.error && (
        <p className="friend-profile__error" role="alert">
          {state.error}
        </p>
      )}
    </form>
  );
}
