# Shared contracts: contributor guide

For teammates and their AI assistants. Scope: `contracts/`. This folder currently
contains instructions only; no implementation, dependencies, or commands are set up.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own canonical interface schemas and shared synthetic messages once their design
is agreed. The integration lead coordinates edits with every affected consumer.

- Start from docs/TEAM-CONTRACT.md; it remains a draft, not an executable schema.
- Define normalized constraints/default metadata, CandidateSet, QuestProposal,
  frontend Quest responses, errors, check-ins, and analytics events consistently.
- Resolve open fields/settings with owners instead of inventing private alternatives.
- Use one authoritative definition per model and derive consumer types where practical.
- Keep example IDs, money, durations, and fact references consistent with data fixtures.
- Coordinate breaking field, unit, enum, or behavior changes with consumers.
- Validate schemas and examples and check actual producer/consumer compatibility.
- This folder currently contains guidance only; no schema has been frozen or generated.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.
