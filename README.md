# Local Quest

A personalized neighborhood adventure planner that connects exploration, playful
challenges, and discovery of local businesses.

Status: quest-generation API implemented in `api/` and verified locally with mock
data. No real dataset, live integration, or deployment exists yet.
This folder is self-contained and can become its own repository later.

## Reading guide

Each requirement has one authoritative home. Link to it rather than duplicating it.

1. [Project brief](PROJECT.md): product, audience, scope, and acceptance criteria.
2. [Agent instructions](AGENTS.md): working rules and skill selection for every chatbot.
3. [Architecture](docs/ARCHITECTURE.md): component responsibilities, developer-owned
   technology choices, folder layout, team workflow, and copyable task prompts.
4. [Shared contract](docs/TEAM-CONTRACT.md): proposed API/data/AI interfaces, examples,
   persistence and sourcing requirements, and interface-change rules.
5. [Build plan](docs/PLAN.md): current phase, work, dependencies, and progress.
6. [Testing](docs/TESTING.md): behavioral, contract, AI, and complete-journey checks.
7. [Deployment and demo](docs/Deployment.md): setup, release checks, recovery,
   rehearsal script, and submission evidence.
8. [Skills catalog](docs/skills.md): available options, unverified candidates,
   and a record of the team's skill selections. Copies of all 13 catalog skills are
   in [.skillls/](.skillls/README.md); tools/accounts are not automatically configured.

Developers choose component technologies while honoring shared contracts and
coordinating cross-component decisions. The contract remains a draft; executable
schemas, automated checks, and application code have not been implemented.

## Generation workflow

Duration/budget/preferences → backend validation and missing-input defaults →
Snowflake top-10 candidate JSON → AI-selected and ordered quest proposal → backend
walking/budget/hours/fact validation → saved quest JSON → frontend display.
Defaults are 90 minutes, $30, and no preference. Default currency and missing
location/time behavior still need confirmation. See the architecture for the flow
and the shared contract for boundary formats. This changes AI from narrative-only
assistance to route planning; code still verifies the result.

## Work areas

Each work area currently contains only its contributor guide:
[frontend](web/AGENTS.md), [backend/AI](api/AGENTS.md),
[Snowflake](snowflake/AGENTS.md), [shared contracts](contracts/AGENTS.md),
[account-storage definitions](data/AGENTS.md), and [cross-component tests](tests/AGENTS.md).
Developers create internal structure when implementing their assigned components.

Snowflake supplies candidate JSON directly to the backend; no local place dataset
or intermediate JSON file in `data/` is required. Actual user accounts live in a
chosen database/authentication service. Service credentials stay in server-side
secret configuration. `data/` contains definitions and guidance, not live records.

## Development
- Backend API (Python/FastAPI): see [api/README.md](api/README.md) for verified commands
  (`pip install -e ".[dev]"`, `python -m app`, `pytest`). Runs offline with labeled mock data by default.
- Frontend (Next.js App Router + Auth.js), from `web/`: copy `.env.example` to
  `.env.local` and fill it in, then `npm install`, `npm run dev`
  (http://localhost:3000), `npm run build`, `npm run typecheck`, `npm run lint`,
  `npm test`. Needs a MongoDB reachable at `DATABASE_URL`. Built: landing, register,
  sign-in, and protected Explore pages; it does not call the quest API yet.
  Account schema: [data/ACCOUNTS.md](data/ACCOUNTS.md).
- API routes, inputs and responses: [api/ROUTES.md](api/ROUTES.md).
- Snowflake procedure (not yet run against an account): [snowflake/find_quest_locations.sql](snowflake/find_quest_locations.sql).

No live services have been provisioned or verified yet.

## License
Undecided. Select an application license before publishing as open source; track
model, dependency, and data licenses separately.
