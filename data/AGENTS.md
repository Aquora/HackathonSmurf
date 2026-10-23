# Account storage: contributor guide

For teammates and their AI assistants. Scope: `data/`. This folder currently
contains instructions only; no implementation, dependencies, or commands are set up.

## Before working

Read the root [AGENTS.md](../AGENTS.md), [product brief](../PROJECT.md),
[architecture](../docs/ARCHITECTURE.md), [shared contract](../docs/TEAM-CONTRACT.md),
and [current plan](../docs/PLAN.md). Consult the [skills catalog](../docs/skills.md)
when selecting skills; read each selected skill's actual instructions.

## Responsibilities and boundaries

Own account-storage definitions, migration files if needed, and non-secret setup
notes. This folder is not a store of actual credentials, user records, or Snowflake
place data. The authentication provider/database is still undecided.

- Coordinate user IDs, ownership relationships, session behavior, and access rules
  with the backend owner before choosing schemas. Backend owns authentication
  handlers and database/provider adapters in api/.
- Actual accounts live in an operational database or authentication service.
  If passwords are managed by the app, store secure password hashes in that database;
  never commit passwords, hashes, session tokens, recovery codes, or account exports.
- Service credentials belong in server environment configuration or a secret manager.
  Record only variable names/purposes and placeholders in shared setup examples.
- A managed authentication provider may eliminate the need for local credential
  schemas; do not create an unnecessary password database or service.
- Snowflake owns the place catalog and sends candidate JSON to the backend.
  Do not write that response into data/ or require a local catalog copy.
- Synthetic test inputs belong in shared contract examples or test fixtures,
  clearly labeled and free of real user data.
- Coordinate account creation/session validation/ownership checks and deletion
  behavior with the backend; no login implementation or provider is configured yet.

## Working agreement

Work within your assigned paths; coordinate changes outside them. Component owners
choose technology while preserving shared interfaces. Create internal folders and
implementation only as required by an assigned, authorized task. This folder setup
alone does not authorize building, installing, or deploying the application.
Communicate assignments and results directly with the team; report actual checks,
mock/live dependencies, and remaining integration needs in chat.
