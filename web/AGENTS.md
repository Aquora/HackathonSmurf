# Frontend: contributor guide

For teammates and their AI assistants. Scope: `web/`.

## Current state

- Stack: Vite + React 19 + TypeScript, plain CSS with tokens in
  `src/styles/tokens.css`, `motion` for Figma-authored animation, self-hosted
  Jersey fonts via `@fontsource`. Tests: Vitest + Testing Library (jsdom).
- Commands (verified): `npm install`, `npm run dev` (port 5173), `npm test`,
  `npm run typecheck`, `npm run build`.
- Built: landing screen from the LocalQuest Figma file
  (`dNPMN12L6f9V9tFchiIdeH`, frame "Main Page", node 1:3). Play links to
  `#/sign-up`, which is a placeholder until the sign-up frame is built.
- Shared UI: `AppHeader`, `PixelButton`, and `PixelSprite` (pixel art stored as
  run data in `sprites.ts`). Reuse these for the other Figma frames.
- No API calls yet; when added, read the base URL from `VITE_API_BASE_URL`.

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
