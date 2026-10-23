# Frontend: contributor guide

For teammates and their AI assistants. Scope: `web/`.

## Current state

- Stack: Next.js 16 (App Router, `src/app`) + React 19 + TypeScript, plain CSS with
  tokens in `src/styles/tokens.css`, `motion` for Figma-authored animation,
  self-hosted Jersey fonts via `@fontsource`.
- Auth: Auth.js v5 (`next-auth@5` beta) in `src/auth.ts` with Google and
  username/password (Credentials) providers, MongoDB via `@auth/mongodb-adapter`,
  JWT session cookies (30 days). Registration and sign-in are server actions in
  `src/features/auth/actions.ts`. Protected pages: `/quests` (signed-in home),
  `/profile`, and the reserved `/friends` prefix via `src/proxy.ts` plus a check in
  each page. Account schema: [data/ACCOUNTS.md](../data/ACCOUNTS.md).
- Commands (verified): `npm install`, `npm run dev` (port 3000), `npm run build`,
  `npm run typecheck`, `npm run lint`, `npm test` (unit), `npm run test:e2e`
  (needs a running app on a disposable database; see `playwright.config.ts`).
- Config: copy `.env.example` to `.env.local`; never commit real values.
- Screens: landing (`/`), register (`/register`), sign-in (`/sign-in`), Quests
  (`/quests`, protected, where users land after sign-in), and Profile (`/profile`,
  protected) from the LocalQuest Figma file (`dNPMN12L6f9V9tFchiIdeH`). The quest
  board shows empty states until quests are stored. The Explore page was removed;
  `/explore` redirects to `/quests` and the Explore tab is a disabled "coming soon" tab.
- Player settings (`/settings`, protected): profile picture upload/remove and Sign out.
  Opened from the header menu and the profile page's "Edit profile" link. No Figma frame
  exists for it; it reuses the sign-up banner and panel styles. Sign out also appears on
  `/sign-in` when already signed in.
- Profile picture: uploaded picture > Google photo > default pixel explorer
  (`src/lib/profile.ts`). Uploads happen on `/settings` via server actions (`src/features/profile/actions.ts`,
  ≤ 2 MB, PNG/JPEG/WebP detected from bytes) stored in MongoDB `avatars` and served by
  `src/app/api/avatars/[userId]/route.ts` to signed-in users. Quest stats, XP, badges,
  and the quest log show empty/zero states until quest progress is tracked.
- Don't run `npm run build` while `npm run dev` is running; the build rewrites `.next`
  and can crash the dev server.
- Header menu (`AppHeader/HeaderMenu.tsx`): Figma "Menu dropdown"; Player settings
  links to `/settings`, Support is "coming soon" until a support destination exists.
- Shared UI: `AppHeader`, `PixelButton`, `WideButton`/`WideLink`, `TextField`/`PasswordField`,
  `AuthBanner`, `BottomNav`, `PlayerAvatar`, `PixelSprite` (pixel art as run data in `sprites.ts`).
- No quest API calls yet. The FastAPI backend does not yet verify these sessions.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own the user interface: duration/budget/preferences form, applied-default display,
quest map/cards, passport, and authorized dashboard presentation.

- Choose the frontend technology and record the choice in the architecture.
- Send structured inputs to the backend and render the validated Quest response.
- Omit blank optional fields so backend defaults apply; display effective inputs
  and defaults returned by the API. Do not maintain competing default rules.
- Use shared contract examples for labeled mock mode; do not invent response fields.
- Keep Snowflake/model/private service credentials out of browser code.
- Handle loading, invalid input, insufficient candidates, provider failure, and
  failed AI planning as distinct states where the contract distinguishes them.
- Verify narrow-screen and keyboard use, response rendering, and the connected flow.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
