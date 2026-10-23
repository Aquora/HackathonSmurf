# Proposed shared contract for contributors and AI assistants

Status: draft `0.2`, October 23, 2026. This is a concrete proposal for agreement,
not an implemented API, validated schema, or authorization to start coding.
The generation sequence and 90-minute/$30/no-preference defaults are owner-confirmed.
Field names and remaining settings are proposed for interface review.

## 1. Shared product promise

Build a mobile-friendly neighborhood adventure with exactly three unique approved
stops, feasible estimated spending and duration, grounded challenges, simulated
check-ins, a passport, and authorized business engagement metrics.

Code owns route feasibility, validation, ownership, and completion integrity.
AI selects and orders candidate stops and writes grounded quest content. Never represent a fixture,
estimate, simulated check-in, or unverified offer as a verified real-world outcome.

## 2. Sources of truth

- `PROJECT.md`: what the product must do and its scope.
- `docs/ARCHITECTURE.md`: developer-owned technology choices and component boundaries.
- `AGENTS.md`: repository working instructions; local instructions add scoped details.
- `docs/PLAN.md` and an assigned task file: current work, ownership, and dependencies.
- This document: proposed team agreement and initial interface vocabulary.
- Future `contracts/openapi.yaml` and referenced schemas: canonical wire formats.
- Future `contracts/examples/`: shared, schema-checked synthetic messages.

Once machine-readable contracts exist, this document must summarize or link to
them rather than become a competing schema. Do not independently maintain the
same model in OpenAPI, hand-written frontend types, and backend models. Generate
representations where practical and verify that actual API behavior matches them.

If documents and schemas disagree, report the specific conflict to the integration
lead and reconcile it with affected owners. Do not silently choose whichever makes
the current task easier. Existing product boundaries remain in effect.

## 3. Ownership and allowed dependencies

The frontend calls the backend HTTP API. It does not access warehouse credentials,
call the model with service credentials, or import backend implementation files.
Browser map assets may use the selected provider's appropriately restricted public
token; that does not expose the backend's service secrets.

Backend domain logic consumes normalized place and route records through adapters.
It does not depend on the casing or layout of raw Snowflake rows. Snowflake queries
must expose agreed aliases and types; the adapter maps them into the shared schemas.

The AI module consumes normalized constraints and Snowflake candidate JSON. It
selects and orders stops only from those candidates; it cannot invent places,
persist check-ins, or authorize rewards. Analytics
consumes stable events and does not become the operational check-in store.

Each task lists allowed edit paths. A cross-boundary need requires coordination
with the owner, not an unannounced edit or a private workaround that changes behavior.

## 4. Common data conventions

- JSON field names use `snake_case`; IDs are opaque strings, never array positions.
- Money uses integer minor units and an explicit currency, such as
  `{ "amount_minor": 2000, "currency": "USD" }`. Do not use floating-point dollars.
- Durations are integer seconds; distances are integer meters.
- Instants use ISO 8601 strings with an offset; local planning also carries an IANA
  timezone. Reject invalid/ambiguous time input rather than guessing silently.
- Coordinates are `{ "latitude": number, "longitude": number }`. Latitude is
  between -90 and 90; longitude is between -180 and 180.
- Unknown is not zero. Nullable fields must be explicitly declared. Required values
  cannot silently disappear; optional and nullable are different schema decisions.
- Shared IDs link catalog records, facts, quest stops, check-ins, and events.
- `demo` marks synthetic data/activity. `simulation` marks simulated completion
  behavior. `fallback_used` marks an alternate content path. None proves live routing.
- No credentials, real check-in tokens, or personal data belong in shared examples.

Before contract freeze, specify input size/range limits, interest vocabulary,
timestamp precision, currency support, enum values, and additional-field behavior
in the machine-readable schema. These details must not be guessed by each team.

## 5. Frontend ↔ backend agreement

### Input normalization and defaults

The core flow uses one `POST /v1/quests` request with structured duration, budget,
and interests. A separate AI preference-parsing endpoint/confirmation step is not
required by this workflow. Free-text interpretation is deferred unless added explicitly.

Map the form's duration to `available_seconds`, preferences to `interests`, and
budget to a money object. Missing optional fields use backend configuration:

- `available_seconds`: 5400 (90 minutes), confirmed by the owner.
- `budget`: $30; proposed enforcement is a 3000-minor-unit cap, not a permission to
  overspend. The dollar currency code is still to be confirmed. USD in examples is
  illustrative, not a finalized default currency.
- `interests`: `[]`, meaning no preference; do not invent favorite categories.
- `return_to_start`: false, preserving the existing route-end proposal.
- `start`, `departure_time`, and `timezone`: fallback policy remains unresolved.
  A configured neighborhood anchor must be labeled as such, not as the user's location.

For the draft contract, omitted fields trigger defaults. Explicit nulls, malformed
values, negative budgets, nonpositive durations, and unsupported currencies are
validation errors. An explicit zero budget is valid and never replaced by $30.
An explicitly supplied empty interests list is valid, not a default application.
Treat the budget money object as a unit: partial objects are invalid. The frontend
should omit blank optional fields rather than send empty strings or null.

Normalize once before retrieval, preserve valid user values, and retain effective
constraints throughout the pipeline. A valid override beats configuration. Validate
fallback configuration itself; missing required fallback settings produce
`CONFIGURATION_ERROR` without guessing. Defaults never replace missing place data.

The response includes `defaults_applied`: a list of `{field, value}` entries, and
`defaults_version` to identify the configuration used. Return the resolved inputs
in `constraints`; display these in the frontend with an edit/regenerate action.
No extra confirmation screen is required. Subsequent planning errors include the
same normalization context in their error details.

### Quest generation

`POST /v1/quests`

Illustrative synthetic request with explicit overrides; its coordinates do not
select the demo neighborhood and USD does not select the default currency:

```json
{
  "start": { "latitude": 34.05, "longitude": -117.75 },
  "departure_time": "2026-10-24T10:00:00-07:00",
  "timezone": "America/Los_Angeles",
  "available_seconds": 5400,
  "budget": { "amount_minor": 2000, "currency": "USD" },
  "interests": ["coffee", "art"],
  "return_to_start": false
}
```

Proposed success: HTTP 201 with a `Quest` object. Its required fields:

- `quest_id`, `created_at`, `constraints` (the effective normalized input), and `title`.
- `stops`: exactly three ordered `QuestStop` records with distinct `place_id` values.
- `route`: `legs`, `walking_seconds`, `visit_seconds`, `total_seconds`,
  `distance_meters`, and `ends_at_start`.
- `estimated_cost`: money object with the total estimated spending.
- `defaults_applied` and `defaults_version` as defined above.
- `assumptions`: user-readable strings explaining estimates and route conditions.
- `mode`: `demo`, `simulation`, and `fallback_used` booleans, plus
  `routing_source` (`provider`, `cache`, or `fixture`).

Each `QuestStop` includes `stop_id`, `place_id`, `name`, `coordinates`,
`planned_arrival`, `planned_departure`, `visit_seconds`, `estimated_cost`,
`why_selected`, `challenge`, `facts`, `place_verified_at`, and `completion`.
`challenge` contains `text` and `fact_ids`. Each fact contains `fact_id`, `text`,
`source_url`, and `verified_at`. `completion` contains `status` (`pending` or
`completed`) and nullable `completed_at`.

Each route leg includes `from` and `to` references (`kind`: `start` or `stop`, with
`stop_id` only for a stop), `walking_seconds`, `distance_meters`, and `geometry`.
Proposed geometry format: GeoJSON LineString, whose coordinate pairs are
**longitude, latitude**. This ordering differs from the named coordinate object;
the adapter and frontend must test it. Include a final return leg only when requested.

Sum of leg walking times equals `route.walking_seconds`; sum of visits equals
`route.visit_seconds`; their sum equals `route.total_seconds` and fits the requested
time. The first slice does not insert unmodeled waiting time: if waiting is added,
extend the time breakdown and feasibility checks first. Estimated stop costs sum
to the total in a single supported currency. Planned visits fit approved opening
windows, and the itinerary follows the leg and visit durations.

`GET /v1/quests/{quest_id}` returns HTTP 200 with the same `Quest` shape and current
completion state, restricted to the owning session/user. A completed check-in does
not rewrite the original planned times or constraint snapshot.

### Failure behavior

All API failures use a consistent envelope, including framework validation failures.
Example for an impossible request:

```json
{
  "error": {
    "code": "NO_FEASIBLE_ROUTE",
    "message": "No feasible three-stop route was found in the evaluated candidate set.",
    "request_id": "demo_request_001",
    "details": {
      "field_errors": [],
      "reason": "NO_VALID_COMBINATION",
      "search_scope": "retrieved_candidates",
      "constraints": {
        "start": { "latitude": 34.05, "longitude": -117.75 },
        "departure_time": "2026-10-24T10:00:00-07:00",
        "timezone": "America/Los_Angeles",
        "available_seconds": 5400,
        "budget": { "amount_minor": 2000, "currency": "USD" },
        "interests": ["coffee", "art"],
        "return_to_start": false
      },
      "defaults_applied": [],
      "defaults_version": "demo_example_v1",
      "suggested_adjustments": [
        { "field": "available_seconds", "message": "Try allowing more time." }
      ]
    }
  }
}
```

Proposed status/code mapping:

- 422 `VALIDATION_ERROR`: malformed or unsupported input; include field errors.
- 422 `NO_FEASIBLE_ROUTE`: deterministic checks establish no route fits the evaluated
  candidate set (including fewer than three eligible candidates); provide adjustments
  without claiming an untested amount of extra time or money guarantees success.
- 401 `AUTH_REQUIRED`: missing or invalid session.
- 403 `FORBIDDEN`: authenticated session lacks business-metrics permission.
- 404 `QUEST_NOT_FOUND`: missing quest or quest not owned by the session.
- 422 `INVALID_CHECK_IN_TOKEN`: invalid scope, expiry, or token.
- 409 `IDEMPOTENCY_CONFLICT`: the same key was used with different request contents.
- 502 `PLAN_GENERATION_FAILED`: model failure or invalid proposal after the bounded
  repair attempt; never imply that no feasible route exists.
- 503 `CONFIGURATION_ERROR`: required default/context configuration is unavailable.
- 503 `DEPENDENCY_UNAVAILABLE`: required provider could not complete the operation.
- 500 `INTERNAL_ERROR`: unexpected failure with a safe message and request ID.

Every envelope includes `field_errors` and `suggested_adjustments`, empty when
irrelevant. A field error has `field` and `message`. No stack traces or secrets.
The frontend handles unrecognized error codes with a safe generic state. After
normalization, error details also include `constraints`, `defaults_applied`, and
`defaults_version`; before normalization succeeds these are omitted. For
`NO_FEASIBLE_ROUTE`, include a reason and `search_scope: "retrieved_candidates"`.
Do not imply the top-10 shortlist proves infeasibility across the whole neighborhood.

### Simulated check-in

`POST /v1/quests/{quest_id}/check-ins`

Required fields: `stop_id`, `check_in_token`, and `idempotency_key`.
The token comes from the QR flow; do not issue every stop's redemption token as
an ordinary quest-response field. Exact issuance and session transport remain
decisions to resolve before implementing this boundary.

Proposed response, HTTP 200 for both first completion and valid repeated requests:

```json
{
  "quest_id": "demo_quest_001",
  "stop_id": "demo_stop_001",
  "completion": {
    "status": "completed",
    "completed_at": "2026-10-24T17:15:00Z"
  },
  "passport": { "completed_stops": 1, "total_stops": 3 },
  "demo": true,
  "simulation": true
}
```

Validate ownership and token rules before completion. Persist the first completion
time; valid duplicates do not create another stamp or logical event. Reusing a key
for different contents returns a conflict. Return current passport progress, which
may advance after other stops complete, rather than promising byte-identical responses.
Expired/invalid tokens do not become valid merely because a stop was completed earlier.
Demo tokens must never redeem real offers.

### Metrics and health

`GET /v1/businesses/{business_id}/metrics?from=<instant>&to=<instant>&include_demo=false`
requires an authorized owner/admin and a bounded interval. Proposed response fields:
`business_id`, `from`, `to`, `data_as_of`, `includes_demo`, `quest_appearances`,
`completed_visits`, and `verified_redemptions`. Use a start-inclusive, end-exclusive
interval. Before freeze, select a maximum interval and define whether demo-inclusive
responses include both demo and real activity; the suggested meaning is both, labeled.

Count appearances as distinct saved quest/place inclusions, visits as distinct
completed quest/stops, and redemptions only with separate verified evidence.
Unavailable redemption tracking returns `null`, not a fabricated zero. Define
place-to-business ownership before exposing metrics; never assume the two IDs match.

`GET /health` returns HTTP 200 and `{ "status": "ok" }` for liveness. It does not
claim that every upstream provider is ready. Define a separate readiness check
if needed; never expose internal credentials or configuration.

## 6. Backend ↔ Snowflake agreement

Define a shared `PlaceRecord` with `place_id`, nullable `business_id`, `name`,
`description`, `tags`, `coordinates`, `timezone`, `opening_intervals`, nullable `estimated_cost`,
`visit_seconds`, `facts`, `source_url`, `verified_at`, `publication_rights`, and `demo`.
Each approved fact uses the fact shape above. Unknown hours are represented as
`opening_intervals: null`; a known closed planning window is an empty list.

Normalize opening information into absolute `opens_at`/`closes_at` intervals covering
the requested planning window. Document how the adapter derives them from local
hours, date exceptions, and daylight-saving changes. A place with unknown necessary
hours or costs cannot prove a strictly feasible quest.

The retrieval request contains `request_id`, `constraints` (including start/time,
duration, budget, and interests), and `limit: 10`. Use parameterized queries.
Snowflake ranks distinct eligible places; the backend adapter exposes a validated
`CandidateSet` JSON object, whether the query returns rows or a native JSON object:

- `request_id`, `retrieved_at`, and `ranking_version`.
- `constraints`: the same normalized input used for retrieval.
- `candidates`: zero to ten `PlaceRecord` objects, each extended with integer `rank`
  starting at 1 and `match_reasons` strings grounded in record tags/attributes.
- `candidate_count`: equal to the length of `candidates`.

Recommended initial ranking: filter the approved neighborhood/currency and required
known data, then order by interest overlap descending, straight-line distance from
start ascending, and `place_id` as a stable tie-breaker. With no preference, omit
the interest criterion. This ranking is proposed; freeze it and its version with
query aliases/types before independent implementation. Coarse cost/time/opening
filters may exclude clearly impossible places but cannot certify a full route.

Return fewer than ten when necessary; do not pad with duplicates or invented data.
Fewer than three yields an insufficient-candidates reason, not an AI request to
invent stops. Unknown hours/costs cannot support strict planning. An empty successful
query and a warehouse failure are distinct. Candidate descriptions and facts remain
untrusted model input, not instructions. Preserve IDs and provenance through JSON.

Analytics uses a shared `AnalyticsEvent` containing `event_id`, `event_type`,
`occurred_at`, `quest_id`, `stop_id`, `place_id`, nullable `business_id`, `demo`, and
`simulation`. Initially use `quest_stop_included` and `stop_completed` events.
Do not emit a redemption event until its separate verification contract exists.
Mint stable IDs once per logical event and preserve them across delivery retries.

Emit inclusion events when a quest is successfully saved, not every time it is
fetched. Emit completion once after a successful atomic completion. Deduplicate
before aggregation. Delivery frequency and durability for the demo must be decided
explicitly; the UI must expose freshness rather than assume an instant warehouse update.

## 7. Backend ↔ AI agreement

`PlanningInput` contains `request_id`, effective `constraints`, `candidate_set`,
`stop_count: 3`, and `objective`. Proposed objective: satisfy hard constraints,
prefer interest matches, and reduce walking. Exact comparison rules remain open;
never promise a globally optimal route. The input may contain measured walking
legs and validation errors for one repair attempt. Never label distance estimates
as verified walking times.

AI returns `QuestProposal` JSON: `title`, `ordered_stops`, and `planning_rationale`.
Each ordered stop contains `place_id`, `why_selected`, and `challenge` with `text`
and `fact_ids`. Exactly three distinct IDs must belong to this candidate set;
fact IDs must belong to their selected place. The model chooses the order. Backend
assigns quest/stop IDs and completion state, and calculates authoritative costs,
arrival/departure times, walking durations, and geometry. Model totals, if emitted
outside the agreed schema, are rejected rather than used as authoritative values.

Validate schema and IDs before requesting directions. Measure chosen walking legs,
calculate the full schedule including visits, and check budget/opening windows.
Check narrative claims against approved facts; a valid fact ID alone is insufficient.
One repair call may use concrete validation failures and the same candidate set;
validate it again. Bound total calls/time. A failed proposal does not demonstrate
infeasibility: return `PLAN_GENERATION_FAILED` unless independent checks prove
`NO_FEASIBLE_ROUTE` within the stated candidate scope. Routing/provider failures
remain dependency errors. Template prose is allowed only for a valid route and
must set `fallback_used`; a fixture must never masquerade as a live route.

Only validated proposals are assembled into the frontend `Quest` response and
persisted. Record model/prompt versions, defaults version, candidate snapshot
references, and ranking version so evaluations can reproduce the planning context.
The frontend never receives raw unchecked model output.

## 8. Contract change procedure

1. Describe the change, reason, producers, consumers, and compatibility impact in
   the task/PR. Reference the contract revision the task started from.
2. The integration lead and affected owners review the shared schema and examples.
3. Update or regenerate consumers and relevant tests. Do not hand-edit generated files.
4. Integrate together, or add a compatible transition before removing the old shape.
5. Record the new revision and check the connected journey on the integrated branch.

Renaming a field, changing units or semantics, adding a required input, changing
an enum, or changing authorization behavior can break a consumer. Even a new optional
response field needs a compatibility check. `/v1` does not permit uncoordinated
breaking changes merely because the URL stays the same.

## 9. Contract freeze and acceptance gate

Before independent implementation, resolve the explicit gaps above and publish
the canonical schemas. The draft is not ready to substitute for those schemas.
Minimum shared examples: successful three-stop quest; invalid request; no feasible
route; dependency failure; initial and duplicate check-in; unauthorized access;
and demo metrics with unavailable verified-redemption tracking. Add omitted-input
defaults, explicit zero budget, invalid supplied values, top-10/partial/empty candidate
sets, AI proposal and revision, out-of-set IDs, infeasible order, and exhausted repair.

All example messages must validate. Fixture IDs, costs, times, and fact references
must agree across the catalog and API examples. Verify responses from actual
backend handlers against the schema, and run frontend consumer tests with those
same examples. Mock responses must come from the shared fixtures, not private
frontend-only JSON.

When implementation exists, required checks should cover schema validity, generated
type drift, relevant component behavior, and the connected journey. These checks
are planned, not configured or run today. A feature is integrated only after its
producer and consumer work together; a chatbot's claim of completion is not evidence.

## 10. Persistence, sourcing, and data lifecycle

The shared record shapes above define exchanged data; storage schemas and migrations
are not implemented. Keep operational storage distinct from warehouse analytics.

### Operational records

- Sessions/users: identity and ownership relationships.
- Quests: owner, effective constraints, defaults applied/version, candidate snapshot
  references and ranking version, approved route snapshot, model/prompt version,
  creation time, and expiry where applicable.
- Stops: quest/stop IDs, place reference, planned times, and challenge fact references.
- Check-ins: unique quest/stop completion, token validation outcome, and idempotency key.
- Event outbox: stable event ID, delivery state, and retry information.

Choose the transactional store before relying on atomic constraints.

### Optional offers

If introduced, record offer ID, business ID, terms, validity window, eligibility,
and merchant verification status. Unverified examples are demo-only. Offers do not
establish partnerships or authorize real redemptions.

### Initial dataset and provenance

Curate 10–15 places in one walkable neighborhood. No real locations have been
selected or verified yet. Catalog descriptions, facts, hours, prices, and coordinates
need documented sources and verification times. Record permission/license and
attribution for every source; do not assume scraped descriptions or map-provider
data can be redistributed. Unknown prices/hours remain unknown or exclude a place
from strict planning. Keep demo fixtures separate from real data.

### Privacy and public-release decisions

Avoid collecting precise movement trails or raw prompts by default. Document metric
semantics and how late-arriving events affect freshness. Before public release,
set retention/deletion periods, owner permissions, backup/restore behavior, ingestion
schedule, and a data correction process.
