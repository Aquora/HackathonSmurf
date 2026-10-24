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
  sign-in, and protected Quests (home after sign-in), quest detail, Friends, and Profile pages. The
  Next.js server calls the quest API (`QUEST_API_URL`) and saves quests in MongoDB.
  Account schema: [data/ACCOUNTS.md](data/ACCOUNTS.md).
- API routes, inputs and responses: [api/ROUTES.md](api/ROUTES.md).
- Snowflake procedure `LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS` (deployed on a trial account): [snowflake/README.md](snowflake/README.md).
- Configuration: one file, `.env` in this folder (template: [.env.example](.env.example)), read by the API and the Snowflake scripts.

## Run the whole app locally

Three processes: MongoDB (accounts and saved quests), the quest API, and the web app.

```bash
# 1. MongoDB (any local or hosted instance works)
docker run -d --name localquest-mongo -p 27017:27017 mongo:7   # later: docker start localquest-mongo

# 2. Config (once). Root .env = API + Snowflake; web/.env.local = logins + API URL.
cp .env.example .env                 # mock data by default; set DATA_PROVIDER/AI_PROVIDER=snowflake + SNOWFLAKE_* for live
cp web/.env.example web/.env.local   # set AUTH_SECRET (npx auth secret), DATABASE_URL=mongodb://localhost:27017/localquest

# 3. Quest API on :8080
cd api && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/python -m app

# 4. Web on :3000 (another terminal)
cd web && npm install && npm run dev
```

Open http://localhost:3000, register, plan a quest on the quest board, check in at each stop,
and see XP/badges on the profile. Mock-mode quests are labeled "Demo".

Checks: `cd api && .venv/bin/python -m pytest`; `cd web && npm run typecheck && npm run lint && npm test`;
end-to-end with both servers running:
`cd web && E2E_DATABASE_URL=mongodb://localhost:27017/localquest E2E_BROWSER_CHANNEL=chromium npx playwright test`
(run `npx playwright install chromium` once; the Google test also needs `E2E_GOOGLE_CLIENT_ID` and real Google credentials).

Verified locally on 2026-10-23 in mock mode (MongoDB in Docker). Live Snowflake/Cortex was verified
earlier by the Snowflake owner but not re-run with this integration. Nothing is deployed.

## License
The application code is released under the [MIT License](LICENSE)
(Copyright (c) 2026 Local Quest contributors).

Models, data, and dependencies keep their own licenses; the MIT License does not cover them:

| Component | Used for | License |
|---|---|---|
| Meta Llama 3.3 70B (`llama3.3-70b`, via Snowflake Cortex `AI_COMPLETE`) | Reading requests and planning routes | [Llama 3.3 Community License](https://www.llama.com/llama3_3/license/) (open weights; includes an acceptable use policy) |
| Snowflake Arctic Embed M v1.5 (`snowflake-arctic-embed-m-v1.5`, via `AI_EMBED`) | Interest-to-category matching | Apache 2.0 |
| OpenStreetMap place and address data | Candidate places, geocoding | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/); show "© OpenStreetMap contributors" wherever the data appears |
| npm and Python dependencies | Web app and API | Each package's own license (see `web/package-lock.json` and `api/pyproject.toml`) |

Snowflake Cortex is a hosted, proprietary service; running the AI steps requires a Snowflake account.
