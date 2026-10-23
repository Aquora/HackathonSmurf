# Local Quest API

Python + FastAPI backend that turns a free-text request into a round-trip quest that
always starts and ends at Cal Poly Pomona (3801 W Temple Ave, Pomona, CA 91768). **Routes, inputs and responses: [ROUTES.md](ROUTES.md).**
Interactive docs at `/docs` (disabled when `APP_ENV=production`).

## Flow (`POST /v1/quests`)

1. Validate `{ message }`. The start/end address is fixed to Cal Poly Pomona (`CAMPUS_LOCATION`
   in `app/domain/types.py`).
2. **Llama** (Snowflake Cortex model) extracts `{ desiredTime, desiredBudget, locationPreference, travelMethod }`.
3. Code normalizes it; missing/invalid values default to `90`, `30`, `"random"`, `"drive"`.
4. **Snowflake** procedure returns candidate locations; code requires exactly 10 unique ones.
5. **Llama** plans a route from those 10 that starts and ends at Cal Poly Pomona.
   Each of the 10 locations is sent with a randomly assigned task (picked by code), and
   The model writes a short description for every stop it chooses.
6. Code validates the route (known places only, no duplicates, ordered times, open at
   departure, within `desiredTime`, catalog costs within `desiredBudget`), asks the model
   once to repair it if invalid, then returns it. `estimatedCost` is summed by code.
   If every candidate is closed or none is affordable, it returns `NO_FEASIBLE_ROUTE`
   with `proven: true` before calling the model.

## Commands (verified 2026-10-23, Python 3.14 locally, 3.13 in Docker)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp ../.env.example ../.env    # one .env for the whole project; defaults run offline with mocks
.venv/bin/python -m app       # http://localhost:8080 — reads ../.env; real env vars win
.venv/bin/pytest              # 73 tests
cp .env.example .env          # defaults run fully offline with mock adapters
.venv/bin/python -m app       # http://localhost:8080 — reads .env; real env vars win
.venv/bin/pytest              # 86 tests

# Print the exact SQL + JSON the API would send to Snowflake (no Snowflake call)
.venv/bin/python -m scripts.snowflake_payload "2 hours, \$25, coffee, walking"

docker build -t local-quest-api .
docker run -p 8080:8080 --env-file ../.env -e APP_ENV=production local-quest-api
```

Requires Python 3.12+. Try it:

```bash
curl -s -X POST localhost:8080/v1/quests -H 'content-type: application/json' \
  -d '{"message":"2 hours, $25, coffee and art, walking"}'   # starts at DEFAULT_START_ADDRESS
  -d '{"message":"2 hours, $25, coffee and art, walking"}'
```

## Configuration

See [../.env.example](../.env.example), the single config file for the API and Snowflake scripts. Key points:

- `AI_PROVIDER=snowflake` runs the model step on Snowflake Cortex (`SELECT AI_COMPLETE(SNOWFLAKE_AI_MODEL, prompt)`,
  default `llama3.3-70b`, open-weight) through the same Snowflake connection pool and login, so no extra key
  is needed. The backend role needs `SNOWFLAKE.CORTEX_USER` (granted in `../snowflake/sql/01_setup.sql`).
  Verified 2026-10-23: a full quest took about 24 s, including one budget repair.
- `DATA_PROVIDER=snowflake` calls `LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS` (see
  [../snowflake/README.md](../snowflake/README.md)) with bound parameters,
  using `snowflake-connector-python` in worker threads with a small connection pool.
  Key-pair auth (`SNOWFLAKE_PRIVATE_KEY_PATH`) is preferred over passwords.
- `APP_ENV=production` refuses mock adapters unless `ALLOW_MOCK_IN_PRODUCTION=true`,
  hides `/docs`, and switches logs to JSON. Mock responses always include `"mock": true`.

## Layout

```text
app/
  __main__.py          process entry: settings, logging, uvicorn
  container.py         wires adapters from settings
  config.py            env validation (pydantic-settings)
  main.py              FastAPI app: routes, error mapping, CORS, security headers, body + rate limits
  services/quest_service.py   orchestrates the flow
  domain/              models, preference defaults, location + route validation (pure)
  adapters/llm/        model prompts and JSON parsing (the client itself is adapters/snowflake/cortex_client.py)
  adapters/snowflake/  pooled connector executor + procedure call
  adapters/mock/       offline fictional data and deterministic planner
tests/                 unit, service, adapter, and HTTP tests
```

## Production notes

- Put it behind HTTPS and set `TRUST_PROXY=true` so rate limits use the real client IP.
- Rate limiting is in-memory per process; use a shared store if you run several instances
  or workers.
- No authentication yet: the endpoint is public. Add auth before exposing paid model usage widely.
- Request bodies (messages) are not logged.
