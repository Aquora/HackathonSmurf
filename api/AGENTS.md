# Backend and AI: contributor guide

For teammates and their AI assistants. Scope: `api/`. This folder currently
contains instructions only; no implementation, dependencies, or commands are set up.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own request validation/defaults, Snowflake/model/routing adapters, quest validation,
persistence, access control, and repeat-safe check-ins. AI is initially part of this
component; assign disjoint internal paths if separate teammates work on it.

- Choose backend technology; coordinate storage, auth, providers, and hosting.
- Follow the architecture's generation flow and the shared contract's input rules.
- Normalize omitted inputs once: 90 minutes, $30, no preference. Currency and
  missing location/time behavior remain unresolved; preserve valid overrides.
- Obtain up to 10 Snowflake candidates; AI selects/orders three candidate IDs.
- Validate AI output and recompute route feasibility from catalog/provider data.
  Never trust model-generated cost/time totals or treat model failure as infeasibility.
- Save only validated quests; enforce ownership and one completion per quest/stop.
- Keep secrets server-side and provider adapters separate from domain rules.
- Test defaults, failures, constraint checks, ownership, duplicate check-ins, and
  grounded AI behavior using isolated fixtures before claiming live integration.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.
