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
| `user_stats` | Nothing yet (read by `web/src/lib/stats.ts`) | `userId`, `questsCompleted`, `placesVisited`, `currentStreakDays`, `lastActiveDay` (`YYYY-MM-DD`, Los Angeles), `badges` (`id` from `BADGES`, `earnedAt`) | `user_stats_user_unique` (unique, created on first use) |
| `avatars` | Profile picture upload (`web/src/features/profile/actions.ts`) | `_id` (= user `_id`), `data` (binary, ≤ 2 MB), `contentType` (`image/png`, `image/jpeg`, or `image/webp`, detected from the file bytes), `size`, `updatedAt` | `_id` only |

A pair of players has at most one `friendships` document. Declining or cancelling a request
deletes it; sending a request to someone who already sent you one accepts theirs. Players are
found by exact username or exact name (case-insensitive), never by partial match.
Either friend can remove an accepted friendship (deletes the document).

Profile stats (quests done, places found, day streak, badges, friend count) are shown on
your own card and to accepted friends at `/friends/<userId>`; other players see only the
name, handle, picture, and join date. `user_stats` has no writer yet, so its counters read
as zero until quest completion is recorded. A streak whose `lastActiveDay` is before
yesterday displays as 0.

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
remove their `users` document and matching `accounts`, `avatars`, `user_stats`, and
`friendships` documents.
