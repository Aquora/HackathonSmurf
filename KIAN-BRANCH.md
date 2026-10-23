# `kian-branch`: enforce budget and time in code

Builds on the backend already on `main` (PR #1). Same API, same camelCase contract; it
makes the server, not the model, guarantee budget and time. Use this file as the PR
description and delete it when the branch merges.

## Why

`AGENTS.md` requires budget, duration, and opening windows to be validated in code and
never trusted from model totals. On `main`, time and budget were soft targets and
`estimatedCost` was whatever the model reported.

## What changes

- **Snowflake returns cost.** `find_quest_locations.sql` adds `estimatedCost` (from the
  existing `ESTIMATED_COST` column) to each location; omitted when unknown.
- **Budget is a hard check.** `validate_route` sums the chosen stops' catalog costs and
  rejects routes over `desiredBudget`. The response's `estimatedCost` is that sum; the
  model's number is ignored. Stops with unknown cost are rejected, since they can't be checked.
- **Time is a hard check.** Rejects routes whose last stop ends after `desiredTime`, or
  whose `totalTime` exceeds it or is shorter than the stops themselves take.
- **Honest `NO_FEASIBLE_ROUTE`.** Errors now include `details.reason` and `details.proven`:
  - `ALL_CLOSED` / `NONE_WITHIN_BUDGET` (`proven: true`): checked before calling the model,
    which saves a model call.
  - `PLANNER_FOUND_NONE` (`proven: false`): the model returned no stops; the UI should
    suggest changes rather than say it's impossible.
- Rejected routes still get the single repair attempt, now with budget/time reasons.
- Mock places have prices; the mock planner stays within budget.
- `api/ROUTES.md`, `api/README.md`, `docs/ARCHITECTURE.md`, `docs/PLAN.md` updated.

## For the frontend

- `quests[].location.estimatedCost` is new (dollars, always present on returned stops).
- `estimatedCost` on the route is now always present and computed by the server.
- Handle `details.proven` on `NO_FEASIBLE_ROUTE` (see ROUTES.md for wording).

## Verification

- `cd api && .venv/bin/pytest`: 73 passed (55 existing + 18 new).
- Ran the server with mock adapters (`python -m app`) and sent real requests:
  $25 coffee/art walk, $0 budget, and $3 budget all returned routes within budget and time.
- Not run: the Snowflake procedure against a real account; any live model.

## Still not verified by code

- Travel times and distances come from the model (no routing provider or coordinates).
- Places only have a closing time, so "open at arrival" can't be checked.
- No approved-facts grounding for challenge text yet.

## History

An earlier standalone backend from this branch (snake_case contract, fixture pipeline) is
preserved as tag `kian-backend-v1` for reference; it was not merged.
