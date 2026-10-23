# Cross-component verification: contributor guide

For teammates and their AI assistants. Scope: `tests/`. This folder currently
contains instructions only; no implementation, dependencies, or commands are set up.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own shared contract checks and complete user-journey checks. Keep component-local
unit tests with their components. Choose test tools compatible with the team's stack.

- Use docs/TESTING.md as the acceptance checklist; do not duplicate it here.
- Check normalization/defaults → candidate JSON → AI proposal → backend validation
  → frontend quest display, then simulated check-in/passport/analytics behavior.
- Cover malformed inputs, missing context, fewer than three candidates, out-of-set
  IDs, infeasible orders, bounded repair, provider failures, and ownership failures.
- Verify actual producer/consumer compatibility, not just matching mock responses.
- Use isolated fixtures/nonproduction resources and label mock versus live checks.
- Record actual commands/results and untested areas. No test commands are established.
- Do not run tests against production or create real merchant redemptions.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.
