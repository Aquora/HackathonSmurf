# Local Quest architecture

Status: proposed design; implementation and integration are unverified.

## Technology ownership

Component developers may choose their languages, frameworks, and local tooling.
Record actual
choices, versions, and rationale here when selected, with verified setup/check
commands in component READMEs. Internal folder layouts may follow those choices.

Shared API/data contracts and product requirements remain binding, including
Snowflake retrieval/analytics and open-weight AI for the proposed demo. Coordinate
choices that affect another component, authentication, shared storage, runtime
compatibility, hosting, or costs with the integration lead and affected owners;
material scope, security, and budget changes still require the product owner.
No component technology has been selected by this documentation change.

## Components
- Web: preference form, map, route cards, passport, and authenticated dashboard.
- API: input validation/defaults, candidate retrieval, AI-plan orchestration,
  constraint validation, quest persistence, and idempotent check-ins.
- Snowflake: curated catalog, ranked top-10 candidate retrieval, and analytics. No browser receives Snowflake credentials.
- Model adapter: candidate-based stop selection/order and grounded quest JSON generation.
- Routing adapter: actual walking paths and durations; straight-line distance is
  only a shortlist filter, never proof of walking feasibility.
- Operational store: durable quests, sessions, check-ins, and event delivery state;
  engine undecided. Do not assume warehouse inserts provide transactional uniqueness.

## Generation flow

Owner-confirmed sequence: form → backend validation/defaults → Snowflake top 10
→ AI quest proposal → backend verification/persistence → frontend JSON display.
The existing three-stop quest remains the demo target; 10 is the candidate limit,
not the number of stops. JSON is exchanged as payloads, not temporary files.

1. Receive duration, budget, preferences, and starting-location/time context.
2. Validate supplied values. Fill omitted duration with 90 minutes (5400 seconds),
   budget with $30 (3000 minor units for a two-decimal dollar currency), and interests
   with an empty list meaning no preference. Use one backend-owned configuration.
   Return effective inputs and applied defaults so users can see and edit them.
   Invalid supplied values do not silently become defaults. Currency code, start
   fallback, timezone, and departure policy must be agreed before implementation;
   never silently invent a location or substitute the server's timezone.
3. Query Snowflake using effective location, preferences, duration, budget, and time
   context. Filter eligible catalog records and rank deterministically; return at
   most 10 distinct candidates with the parameters needed for planning. Fewer than
   10 is valid; fewer than three cannot yield the current three-stop quest.
4. Give the AI effective constraints and the candidate JSON. AI selects and orders
   three candidate IDs and creates a themed quest with grounded challenges. The
   proposed objective is relevance and shorter walking, subject to hard constraints;
   define ranking/optimization rules before benchmarking. No global-optimality claim.
5. Validate the AI schema, candidate membership, uniqueness, and factual references.
   Obtain actual walking legs for its chosen order. Recompute costs, visits, arrival
   times, opening-window checks, and total duration from trusted records/provider
   data. Model-generated travel times or totals are never evidence of feasibility.
6. If validation fails, allow at most one revised proposal using concrete failure
   reasons and available measured legs, within a request time budget. Revalidate it.
   A model failure is not proof no feasible route exists. Distinguish invalid-plan,
   provider, insufficient-candidate, and demonstrated-infeasibility outcomes.
7. Save only a validated quest; backend assigns IDs and constructs the authoritative
   response JSON with effective constraints, defaults, route geometry, verified
   calculations, source references, and simulation flags. Frontend renders it.

## Planning efficiency and boundaries

Use a bounded top-10 input to limit model context and latency. Request walking legs
for proposed routes rather than prefetching every pair by default. Reuse measured
legs within the request; cross-request caching depends on provider rights/freshness.
Straight-line distance can inform candidate ranking but never verify walking time.
If evaluation shows poor route quality, assess a bounded walking matrix or code-based
comparison before expanding complexity or cost. Final optimization weights and
quality/latency targets remain to be measured and agreed.

Default values apply only to user-input omissions. Missing catalog hours, costs,
facts, or coordinates must never be fabricated from those defaults. If a required
application fallback is unconfigured, return a configuration error rather than a
false quest. Return applied defaults even on post-normalization planning errors.


## Check-in and analytics
The API verifies session ownership and a valid stop token, then atomically records
one completion per quest/stop. Emit an event with a stable event ID. For production,
use durable delivery state and retryable export to Snowflake; deduplicate by event
ID. Dashboard counts never equate impressions or check-ins with purchases.
Demo QR codes are simulations; public redemptions require stronger merchant-backed
verification. Exact operational storage and ingestion are open decisions.

## Resilience
Use bounded timeouts/retries per provider. Invalid model output may receive one
repair attempt, then a clear planning failure. Approved template text can replace
invalid prose only when the underlying route has independently passed validation.
Unavailable routing cannot silently become a verified walking route. Mark cached
facts with their verification time and handle unknown opening hours explicitly.

## Team organization


Use one shared repository with separate ownership areas. Every teammate should
clone the whole repository, even if they only edit one folder. Every AI assistant
needs access to the same root instructions, product brief, contracts, and examples.
Giving each teammate only their own folder removes the context needed to integrate.

Folders reduce editing collisions. Shared contracts prevent incompatible behavior.
Frequent integration proves that the pieces actually work together. All three are
needed; resolving Git conflicts alone cannot fix mismatched field names or logic.

## Proposed folder layout

The main work areas `web/`, `api/`, `snowflake/`, `contracts/`, `data/`, and
`tests/` now exist with only an AGENTS.md contributor guide in each. Existing root
documents and `docs/` remain. The tree below shows possible future internal paths,
not files already created. Add nested directories only when implementation needs them.
The internal source layout can be adjusted after the framework choices are confirmed.

```text
local-quest/
├── AGENTS.md                   Shared instructions for every AI assistant
├── PROJECT.md                  Product scope and acceptance criteria
├── README.md                   Onboarding and verified development commands
├── web/                        Frontend application
│   ├── AGENTS.md               Frontend-specific boundaries and checks
│   ├── src/
│   │   ├── app/                Pages and navigation, if Next.js is selected
│   │   ├── components/         Shared interface elements
│   │   ├── features/           Preferences, quest, passport, dashboard
│   │   └── lib/api/            API client and generated contract types
│   └── tests/                  Frontend behavior and accessibility tests
├── api/                        Backend application
│   ├── AGENTS.md               Backend-specific boundaries and checks
│   ├── app/
│   │   ├── routes/             HTTP handling and session/access checks
│   │   ├── domain/             Planning rules and constraint validation
│   │   ├── services/           Quest/check-in orchestration
│   │   ├── adapters/           Snowflake, routing, and storage integrations
│   │   └── ai/                 Model adapter, prompts, output validation
│   └── tests/
│       └── ai/                 Repeatable AI evaluation cases
├── snowflake/                  Warehouse objects and queries
│   ├── AGENTS.md               Data ownership, query interfaces, safe checks
│   ├── migrations/             Versioned catalog/event/view schema changes
│   ├── queries/                Candidate retrieval and metrics queries
│   └── tests/                  Data quality and query-result checks
├── contracts/                  Canonical interfaces shared by all teams
│   ├── README.md               Contract revision, owners, generation commands
│   ├── openapi.yaml            HTTP requests, responses, and error schemas
│   ├── schemas/                Shared place, event, and AI boundary schemas
│   └── examples/               Shared synthetic success and failure examples
├── data/                       Small approved data and provenance records
│   ├── fixtures/               Synthetic catalog inputs used by tests
│   ├── curated/                Approved redistributable neighborhood records
│   └── SOURCES.md              Sources, rights, attribution, verification dates
├── tests/
│   ├── contracts/              Producer/consumer compatibility checks
│   └── e2e/                    Complete cross-component user journeys
├── scripts/                    Shared setup/check scripts, once verified
├── docs/                       Architecture, decisions, plans, team guidance
│   └── tasks/                  One scoped task and handoff file per work item
└── .github/
    ├── workflows/              Automated checks, if GitHub Actions is selected
    └── CODEOWNERS              Review ownership, if GitHub is selected
```

`contracts/examples/` contains messages exchanged between components.
`data/fixtures/` contains source records used to produce those messages. Reuse
stable fixture IDs and reference files rather than copying competing datasets.

Do not add a separate AI server just to give an AI teammate a folder. Initially,
`api/app/ai/` provides a clear ownership area within the proposed backend. A separate
service would require a justified architecture decision and another interface.

## Assign work by skills, not by a fixed team size

### Frontend and design contributor

Owns `web/`. Builds preference entry and applied-default display, map and stop cards, passport,
dashboard presentation, and loading/error/empty states. Uses the shared contract
examples while the backend is being built. Does not invent response fields, call
Snowflake directly, or become the authority on budget and route feasibility.

Acceptance: the interface handles the agreed success and failure examples, works
on a narrow screen and with a keyboard, and later passes the same flow against the API.

### Backend contributor

Owns backend routes, domain rules, orchestration, service adapters, and local tests.
Builds the planner, persistence, ownership enforcement, and repeat-safe check-ins.
Uses agreed data and AI interfaces. Does not quietly change the HTTP contract to
match a convenient implementation.

Acceptance: API responses match the contract; constraints, ownership, dependency
failures, and duplicate check-ins behave correctly under controlled tests.

### AI contributor, if there is a separate teammate

Owns `api/app/ai/` and `api/tests/ai/`, explicitly excluded from the backend
contributor's concurrent editing scope. Builds route proposals and grounded
challenges using effective constraints and only the top-10 candidate records.

Acceptance: agreed evaluations cover valid output, invented facts/IDs, hostile
retrieved text, and timeout/repair/fallback behavior. Model and prompt versions
and actual results are recorded.

### Snowflake and data contributor

Owns `snowflake/` and assigned `data/` paths. Defines catalog objects, curated
records, parameterized ranked top-10 queries, and deduplicated analytics views. Coordinates
query-result shapes with the backend owner. The backend owner retains the
Snowflake connection adapter unless a task explicitly assigns it elsewhere.

Acceptance: dataset rights and verification are recorded; query outputs match
the agreed shapes; simulated events and repeated event IDs cannot inflate real metrics.

### Integration lead

Owns shared contracts, root configuration, architecture, integration checks, and
the current plan. Reviews interface changes with the people consuming them and
maintains a working integrated branch. Can also hold another role on a small team.

Acceptance: every merged feature works with its consumers, and a full journey is
regularly demonstrated using the latest integrated code.

A teammate focused on research, design, or QA can own curated-data verification,
screen specifications, acceptance scenarios, or demo rehearsal without building
a whole service. Define a small deliverable with explicit inputs and outputs.

## What each chatbot reads

Use [TEAM-CONTRACT.md](TEAM-CONTRACT.md) as the common working agreement.
Every assistant reads the root `AGENTS.md`, `PROJECT.md`, architecture,
plan, and that agreement before its assigned task. It then
reads relevant schemas/examples and its local instructions.

When creating local `AGENTS.md` files, keep them short: owned paths, dependencies,
applicable contracts, verified commands, and acceptance criteria. Link to shared
rules instead of duplicating the product brief in every folder.

Do not assume every AI product automatically discovers `AGENTS.md`, particularly
when launched inside a subfolder. Explicitly give it the reading list and repository
root. If it cannot access the shared context, supply that context before it builds
an interface-dependent feature. Chats do not share memory; committed files do.

## Start integration before splitting up the implementation

1. Choose the first slice: submit preferences and display a saved three-stop quest
   from a clearly labeled synthetic fixture.
2. Review and merge the canonical contract and matching examples first. Assign an
   owner to each boundary. Decide session/auth behavior before implementing protected
   operations; do not create incompatible temporary auth schemes in each component.
3. Establish one working frontend-to-backend call with the fixture response. Record
   verified startup and check commands. This establishes the connection everyone extends.
4. Split tasks along the agreed boundaries. Frontend uses a mock HTTP handler built
   from the shared example; backend and data contributors use the same IDs and shapes.
5. Replace fixture-backed adapters with real catalog, routing, model, and storage
   integrations incrementally. Keep fixture mode visibly labeled.
6. Extend the connected journey through simulated check-in, passport, and analytics.

## Copyable opening message for a teammate's AI

```text
You are working on Local Quest in <repository root>.
Read root AGENTS.md, PROJECT.md, docs/ARCHITECTURE.md,
docs/PLAN.md, and docs/TEAM-CONTRACT.md.
Then read relevant contracts/examples and local AGENTS.md files.

Your task is <task description>. Edit only <assigned paths>. Use the agreed contract
revision. Do not invent interface fields or change another component's boundary
unilaterally. If a required contract is missing or contradictory, report the exact
gap and continue work that does not depend on resolving it.

Before editing, summarize the task, dependencies, and acceptance criteria.
When finished, report changed files, actual check results, mock/live status, and
remaining integration needs in the chat. Follow current task authorization;
the existence of this template does not authorize implementation or deployment.
```

## Decisions needed to adopt the proposal

Assign actual people to roles, confirm the repository host and integration lead,
review the first contract revision, and choose the unresolved infrastructure needed
for the first slice. Roles may be combined; no particular team size is assumed.

## Open decisions and history

Operational database, session/auth design, provider selection, ingestion frequency,
retention, ranking weights, optimization targets, default currency, start/time
fallbacks, latency targets, and release costs remain open.

- 2026-10-22: Local Quest documentation isolated from the reusable parent starter.
- 2026-10-23: release target scoped to a verified hackathon demo; team ownership and
  interface proposals documented. Component developers may choose their technology
  within shared contracts and coordinated deployment constraints.
- Documentation consolidated here for architecture, folder ownership, and team
  workflow. Implementation and canonical schemas remain unverified/unimplemented.
- Owner finalized top-10 retrieval followed by AI route planning. Missing duration
  defaults to 90 minutes, budget to $30, and preferences to none. Backend remains
  responsible for final validation and authoritative response assembly.
