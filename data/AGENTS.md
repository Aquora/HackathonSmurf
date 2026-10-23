# Data and fixtures: contributor guide

For teammates and their AI assistants. Scope: `data/`. This folder currently
contains instructions only; no implementation, dependencies, or commands are set up.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own small synthetic fixtures, approved redistributable catalog records, and source
provenance. Coordinate place/fact IDs and record shapes with Snowflake and contracts.

- Curate the agreed neighborhood only after the location/source decisions are made.
- Record source, permission/license, attribution, verification time, and demo status.
- Keep synthetic fixtures clearly separate from verified real places.
- Never invent prices, opening hours, accessibility details, offers, or partnerships.
- Keep fixture IDs and facts aligned with shared API and AI examples.
- Do not store credentials, personal movement trails, or raw user prompts here.
- Check required fields, unique IDs, references, and publication rights before use.
- No real dataset is present or verified yet; schema/source decisions remain open.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.
