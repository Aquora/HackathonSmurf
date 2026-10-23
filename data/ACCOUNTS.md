# Account storage (MongoDB)

Status: implemented in `web/` and verified against a disposable local MongoDB.
No hosted database has been provisioned. The authoritative index definitions are in
[`web/src/lib/db.ts`](../web/src/lib/db.ts); they are created idempotently on the
first database connection, so no separate migration step is needed.

The database is named by the path in `DATABASE_URL` (for example
`mongodb://localhost:27017/localquest`). Collection names are the Auth.js MongoDB
adapter defaults.

## Collections

| Collection | Written by | Fields | Indexes |
|---|---|---|---|
| `users` | Registration server action; Auth.js adapter (Google) | `name`, `email` (lowercase), `emailVerified`, `image`, `username` (lowercase), `passwordHash` (Argon2id), `createdAt` | `username_unique` and `email_unique` (unique, partial: only where the field is a string) |
| `accounts` | Auth.js adapter | Standard OAuth account link (`provider`, `providerAccountId`, `userId`, tokens) | `provider_account_unique` (unique), `account_user` |
| `sessions` | Auth.js adapter | `sessionToken`, `userId`, `expires` | `session_token_unique` (unique) |
| `verification_tokens` | Auth.js adapter | `identifier`, `token`, `expires` | `verification_token_unique` (unique) |
| `friendships` | Friends page server actions (`web/src/features/friends/actions.ts`) | `requesterId`, `recipientId`, `pairKey` (both ids sorted and joined), `status` (`pending` or `accepted`), `createdAt`, `acceptedAt` | `pair_unique` (unique), `recipient_status`, `requester_status` (created on first use, in `web/src/lib/friends.ts`) |
| `quests` | Quest board server actions (`web/src/features/quests/actions.ts`) | `userId`, `request` (the player's text), `route` (the API's validated `QuestRoute`, stored as returned), `checkIns` (one date-or-null per stop), `status` (`active` or `done`), `mock`, `createdAt`, `startedAt` (set by Start quest; absent before), `completedAt` (set by Finish quest) | `quest_user_created` (created on first use, in `web/src/lib/quests.ts`) |
| `avatars` | Profile picture upload (`web/src/features/profile/actions.ts`) | `_id` (= user `_id`), `data` (binary, ≤ 2 MB), `contentType` (`image/png`, `image/jpeg`, or `image/webp`, detected from the file bytes), `size`, `updatedAt` | `_id` only |

A pair of players has at most one `friendships` document. Declining or cancelling a request
deletes it; sending a request to someone who already sent you one accepts theirs. Players are
found by exact username or exact name (case-insensitive), never by partial match.

`users.avatarUpdatedAt` is set while an uploaded picture exists. The profile shows the
uploaded picture first, then the Google account photo (`users.image`), then the default
pixel explorer from the Figma design. Uploaded pictures are served only to signed-in
users from `/api/avatars/<userId>`.

Notes:

- Password accounts have `username` and `passwordHash`. Google-only accounts have
  neither; the partial indexes allow many documents without a username.
- Sessions use the JWT strategy (required by the Auth.js Credentials provider), so
  `sessions` and `verification_tokens` currently stay empty. They exist so the
  adapter schema is complete if database sessions or email sign-in are added.
- `passwordHash` is never selected into a session, token, or client response.

## Existing data

There were no user records before this change. If accounts are imported later,
lowercase `username` and `email` first and resolve duplicates before the unique
indexes are built. Imported Argon2 hashes in standard PHC format verify as-is;
other formats (such as bcrypt) would need a verifier added in
`web/src/lib/password.ts` and rehash-on-login, or a password reset flow (not yet
implemented).

## Retention and deletion

Not yet decided (see PROJECT.md "Decisions for the owner"). Deleting a user should
remove their `users` document and matching `accounts`, `avatars`, `friendships`, and `quests` documents.

Quest check-ins are simulated (a button, no QR or merchant check). A check-in only sets a
stop's `checkIns` entry while it is still null, so repeating it never adds a second stamp or XP.
Check-ins are accepted only after Start quest (quests saved before that button count as started
once they have a check-in). Finish quest marks the quest `done` only when every stop has a
check-in; it never happens automatically.
Every read and write filters by `userId`, so players only see and change their own quests.
