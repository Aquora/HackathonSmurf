# Local Quest API

FastAPI backend. Status: `POST /v1/quests` runs the full pipeline end to end on
**fixture adapters only**: a synthetic 9-place catalog, a template planner (not AI),
straight-line walking estimates, and an in-memory store. Every response says so in
`mode` (`demo`, `fallback_used`, `routing_source: "fixture"`) and `assumptions`.
No Snowflake, model, routing provider, or database is connected.

## Setup (verified 2026-10-23 on macOS, Python 3.13)

Requires Python 3.11+.

```bash
cd api
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env   # then set LQ_DEFAULT_CURRENCY
```

## Commands

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000   # dev server; docs at /docs
.venv/bin/pytest -q                                   # tests (62 passing)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Layout

- `app/main.py`: app factory, request-ID middleware, routers.
- `app/config.py`: `LQ_*` environment settings and defaults.
- `app/errors.py`: shared error envelope and handlers.
- `app/domain/models.py`: record shapes from docs/TEAM-CONTRACT.md draft 0.2.
- `app/domain/normalization.py`: request validation and missing-input defaults.
- `app/domain/verification.py`: recomputes and checks an AI proposal's route.
- `app/domain/quest.py`: planner input and the frontend `Quest` response shape.
- `app/services/ports.py`: adapter interfaces (`CandidateSource`, `Planner`, `Router`,
  `QuestStore`). Live adapters implement these and are selected in `app/main.py`.
- `app/services/quest_service.py`: orchestration, one bounded repair, provable
  infeasibility checks, and response assembly.
- `app/adapters/`: fixture catalog, straight-line router, in-memory store.
- `app/ai/template_planner.py`: deterministic stand-in for the model planner.
- `app/routes/`: HTTP handlers (`/health`, `/v1/quests`).
- `tests/`: unit and API tests using synthetic, demo-labeled fixtures.

## Try it

```bash
curl -s -X POST localhost:8000/v1/quests -H 'content-type: application/json' -d '{
  "start": {"latitude": 34.0565, "longitude": -117.75},
  "departure_time": "2026-10-24T10:00:00-07:00",
  "timezone": "America/Los_Angeles",
  "interests": ["coffee", "art"]
}'
```

Fixture places sit around (34.0565, -117.75) and are open roughly 06:00-22:00
Los Angeles time; starts far away or late at night return `NO_FEASIBLE_ROUTE`.

## Error outcomes

- `NO_FEASIBLE_ROUTE` (422) only when a sound check over the retrieved candidates
  proves it: fewer than 3 plannable places (`INSUFFICIENT_CANDIDATES`), three
  shortest visits exceed the time (`TIME_BELOW_MINIMUM`), fewer than 3 open long
  enough in the window (`CLOSED_DURING_WINDOW`), or three cheapest exceed the budget
  (`BUDGET_BELOW_MINIMUM`).
- `PLAN_GENERATION_FAILED` (502) when two planner attempts (initial plus one repair
  with the concrete violations and measured legs) fail verification.
- `DEPENDENCY_UNAVAILABLE` (503) when the catalog or routing adapter fails.

## Assumptions pending team decisions

- Currency and start/timezone/departure fallbacks are unset by default; requests
  needing them fail with `CONFIGURATION_ERROR`. No departure-time fallback exists yet.
- Unknown request fields are rejected (`extra="forbid"`). Interests are trimmed,
  lowercased, and de-duplicated; vocabulary is not yet restricted.
- Proposed limits: 8 hours max duration, 100000 minor units max budget, 10 interests
  of up to 40 characters.
- `departure_time` offset must match the timezone at that instant (DST-aware).
- Each challenge must cite at least one fact of its own place. Checking narrative
  claims against fact text is not implemented.
- Fixture catalog prices are in USD; with another configured currency every
  place is filtered out (`INSUFFICIENT_CANDIDATES`), as a real currency filter would.
- `GET /v1/quests/{id}` is not exposed: it must be restricted to the owning session,
  and session/auth design is undecided. Quests are saved in memory only.
- Unknown routes return `NOT_FOUND`/`METHOD_NOT_ALLOWED`, codes not yet listed in the
  contract; clients treat unrecognized codes generically.
