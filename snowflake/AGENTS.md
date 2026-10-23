# Snowflake and analytics: contributor guide

For teammates and their AI assistants. Scope: `snowflake/`. Design is in
[PLAN.md](PLAN.md); layout, verified commands, and deploy steps are in [README.md](README.md).
Not yet deployed to Snowflake; `scripts/lq.py` runs setup, loads, and calls.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own warehouse schema changes, ranked candidate queries, and analytics views.
Own catalog sourcing/ingestion and provenance; coordinate query outputs with the API owner.
The backend connection adapter belongs to api/ unless explicitly reassigned.

- Supply candidate JSON directly to the backend through the query adapter; no
  local place dataset or intermediate data/ JSON file is required.
- Maintain source, attribution, publication rights, and verification metadata with
  the Snowflake catalog; document ingestion procedures in this work area when built.
- Use parameterized queries and versioned, reviewable schema changes.
- Receive effective location/time, budget, duration, and preferences from the API.
- Return up to 10 distinct ranked approved locations with planning parameters,
  facts, verification times, and source metadata matching CandidateSet/PlaceRecord.
- Agree on ranking/version and exact query shapes before independent implementation.
- Do not pad short results or invent unknown prices, hours, coordinates, or facts.
- Distinguish successful empty queries from service errors.
- Deduplicate analytics by stable event IDs and keep demo activity identifiable.
- Check ranking determinism, output types, data quality, and metric definitions.
- Schema files do not authorize applying migrations or using production resources.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.
