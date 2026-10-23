# `kian-branch`: backend scaffold

What this branch adds on top of `main`, how to run it, and what is still missing.
Delete or fold this file into the PR description when the branch merges.

## TL;DR

- Backend is **FastAPI** (Python 3.11+), in `api/`.
- `POST /v1/quests` returns a full three-stop quest in the shared-contract shape,
  **using stand-in data only**: a synthetic 9-place catalog, a template planner (not
  the AI), straight-line walking estimates, and an in-memory store.
- Every response labels this in `mode` and `assumptions`. Nothing live is connected:
  no Snowflake, no model, no routing provider, no database.
- 62 local tests, ruff lint/format clean. Not deployed.

## Run it

```bash
cd api
python3.13 -m venv .venv            # any Python 3.11+
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- Interactive API docs: http://localhost:8000/docs (OpenAPI JSON at `/openapi.json`)
- Tests: `.venv/bin/pytest -q`
- Lint: `.venv/bin/ruff check . && .venv/bin/ruff format --check .`

Sample request (fixture places sit around this start point, open ~06:00–22:00 LA time):

```bash
curl -s -X POST localhost:8000/v1/quests -H 'content-type: application/json' -d '{
  "start": {"latitude": 34.0565, "longitude": -117.75},
  "departure_time": "2026-10-24T10:00:00-07:00",
  "timezone": "America/Los_Angeles",
  "interests": ["coffee", "art"]
}'
```

## What's implemented

| Area | Status |
| --- | --- |
| `GET /health` | Done |
| Shared error envelope + `X-Request-ID` | Done, for every failure including bad JSON and crashes |
| Input defaults (90 min / $30 / no preference) | Done; listed in `defaults_applied` |
| Input validation (nulls, negatives, currency, timezone/DST offset, limits) | Done |
| Route verification (stops in set, facts, hours, budget, time, currency) | Done, recomputed from catalog data |
| One bounded planner repair, then `PLAN_GENERATION_FAILED` | Done |
| `NO_FEASIBLE_ROUTE` only when provably impossible, with suggested fixes | Done |
| Snowflake candidate adapter | **Stand-in** (synthetic catalog) |
| AI planner | **Stand-in** (template planner) |
| Walking routes | **Stand-in** (straight line × 1.3) |
| Quest storage | **In memory**, lost on restart |
| `GET /v1/quests/{id}`, check-ins, passport, metrics | Not started (need session/auth decision) |

Details, file layout, and error outcomes are in [api/README.md](api/README.md).

## For other teams

- **Frontend:** you can build against `POST /v1/quests` now. Field names follow
  `docs/TEAM-CONTRACT.md` draft 0.2. Show `assumptions` and `defaults_applied` to the
  user, and treat `mode.demo` / `mode.fallback_used` as "label this as a demo".
  Route `geometry` coordinates are `[longitude, latitude]`.
- **Snowflake:** the backend expects a `CandidateSet` of up to 10 `PlaceRecord`s
  (see `api/app/domain/models.py`). Please agree query column names/types with the
  backend before writing the adapter. The fixture ranking mirrors the contract
  proposal: interest overlap, then distance, then `place_id`.
- **AI:** a real planner implements the `Planner` interface in
  `api/app/services/ports.py` and returns a `QuestProposal`. It only picks and orders
  candidate IDs and writes challenge text citing fact IDs; the backend computes all
  times and costs. Repair input includes the concrete violations and measured legs.

## Decisions the team still needs to make

- **Currency** for the $30 default (`.env.example` uses `USD` for local dev only).
- **Missing start/timezone/departure time**: fallback policy. Currently these fail
  with `CONFIGURATION_ERROR` unless the request supplies them.
- **Model + hosting** for the open-weight AI planner.
- **Walking-route provider** (OSRM, Mapbox, Google, …).
- **Database and session/auth** design (blocks `GET /v1/quests/{id}` and check-ins).
- **Input limits** proposed here: 8 h max duration, $1,000 max budget, 10 interests.
- **Contract ownership**: whether `contracts/openapi.yaml` is generated from this API.
- Two error codes were added beyond the contract list: `NOT_FOUND` and
  `METHOD_NOT_ALLOWED` for unknown routes.
