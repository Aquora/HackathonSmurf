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
   and a record of the team's skill selections.

Developers choose component technologies while honoring shared contracts and
coordinating cross-component decisions. The contract remains a draft; executable
schemas, automated checks, and application code have not been implemented.

## Development
- Backend API (Python/FastAPI): see [api/README.md](api/README.md) for verified commands
  (`pip install -e ".[dev]"`, `python -m app`, `pytest`). Runs offline with labeled mock data by default.
- API routes, inputs and responses: [api/ROUTES.md](api/ROUTES.md).
- Snowflake procedure (not yet run against an account): [snowflake/find_quest_locations.sql](snowflake/find_quest_locations.sql).

No live services have been provisioned or verified yet.

## License
Undecided. Select an application license before publishing as open source; track
model, dependency, and data licenses separately.
