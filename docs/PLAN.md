# Local Quest implementation plan

Current phase: API quest-generation slice implemented locally (mock-verified); live Cursor/Snowflake integration not yet verified.

## 1. Confirm scope and dependencies
- [ ] Select neighborhood, validate event rules, and confirm the first demo scope.
- [ ] Choose model/runtime, map/routing provider, storage, authentication, and
  operating budget. Confirm default currency and missing start/time behavior.
- [ ] Configure confirmed input defaults: 5400 seconds, $30, and no preference;
  agree on ranking/objective rules and record the configuration version.
- [ ] Component owners select their technologies and record integration/deployment
  implications in ARCHITECTURE.md.
- [ ] Verify service access and required skill/tool availability.
- [ ] Review skills.md together and record selected, optional, or deferred skills
  for each contributor's environment.

## 2. Establish interfaces and working skeleton
- [ ] Review ARCHITECTURE.md and TEAM-CONTRACT.md; assign actual owners and
  select the shared repository/integration workflow.
- [ ] Resolve draft contract gaps, including session transport, query shapes,
  limits, defaults metadata, CandidateSet/QuestProposal/Quest schemas, and event
  delivery; freeze the first agreed contract revision.
- [ ] Create canonical API contracts and synthetic fixtures under contracts/examples/
  and relevant tests; do not require local place data in data/.
- [ ] Choose account storage/authentication and coordinate definitions in data/
  with backend handlers; do not store live credentials or account records in files.
- [ ] Scaffold frontend/backend; verify install/build/test commands in README.
- [ ] Demonstrate a form calling the backend and rendering a labeled fixture quest.

## 3. Parallel implementation after contracts stabilize
- [ ] Frontend worker: form/default display, route map/cards, passport, dashboard UI in web/.
- [ ] Backend/AI worker: normalization, AI candidate selection/order, grounding, verification, persistence in api/.
- [ ] Snowflake worker: catalog sourcing/provenance, ranked top-10 queries, event views
  in snowflake/; supply candidate JSON directly to the backend.
- [ ] Account-storage owner (may be backend teammate): definitions/migrations and
  non-secret setup notes in data/; provider/database choice remains open.
- [ ] Lead: shared contracts, configuration, integration, documentation, and review.
Use separate worktrees or disjoint file ownership; do not allocate agents needlessly.

## 4. Complete the real journey
- [ ] Normalize partial input; expose applied defaults without overwriting valid input.
- [ ] Query Snowflake and validate at most 10 distinct candidate records as JSON.
- [ ] Generate an ordered three-stop AI proposal and grounded challenges.
- [ ] Verify chosen walking legs, costs, visits, hours, and facts; exercise the bounded
  repair path and distinguish failed generation from proven infeasibility.
- [ ] Persist validated quests and render the final JSON including default metadata.
- [ ] Complete an idempotent simulated check-in and reflect it in analytics.
- [ ] Exercise failure cases and independently review relevant changes.

## 5. Hackathon demo and deployment
- [ ] Follow TESTING.md and record actual results.
- [ ] Rehearse the demo script in Deployment.md with honestly labeled simulations.
- [ ] Select repository license; document models, data, setup, and event provenance.
- [ ] Complete `Deployment.md` with verified setup, deploy, smoke-check, and
  rollback steps for the selected demo providers.
- [ ] Deploy the demo and record smoke-check results and the shown version.

## Task handoff
For each task record owner, editable files, dependencies, acceptance checks,
actual results, assumptions, and remaining issues. Lead maintains this plan.

## Verified progress
- [x] Created Local Quest-specific Markdown package on 2026-10-22.
- [x] Documented proposed team ownership, integration workflow, and shared contract
  vocabulary on 2026-10-23; proposals remain unimplemented and unapproved.
- [x] Consolidated documentation into eight core files; preserved team workflow,
  contracts/data requirements, demo guidance, and skill-selection rules.
- [x] Owner confirmed the generation sequence and 90-minute/$30/no-preference defaults.
- [ ] Owner has reviewed remaining contract/configuration decisions.
- [x] Restored a separate skills catalog for team selection; documentation now has
  nine files. No skill installation or mandatory selection was performed.
- [x] 2026-10-23: Implemented `POST /v1/quests` in `api/` (Python/FastAPI, replacing a
  same-day TypeScript draft) with Cursor-style model adapter, Snowflake procedure adapter,
  mock adapters, route validation, and 55 passing tests. Verified locally and in Docker in
  mock mode only. Not verified: live model gateway, Snowflake procedure. Open: which
  endpoint serves "Cursor".
- [x] 2026-10-23: Budget and time enforced in code on the main backend: Snowflake returns
  `estimatedCost`, code sums stop costs and rejects over-budget/over-time routes, and
  provable infeasibility (all closed, nothing affordable) returns `NO_FEASIBLE_ROUTE`
  with `proven: true` before calling the model. 73 tests pass; mock server smoke-checked.
  Earlier standalone backend preserved as tag `kian-backend-v1`.
- [x] Created six main work areas with AGENTS.md contributor guides only; no nested
  source folders, dependencies, application code, or executable tests were added.

- [x] Copied eight existing skills and downloaded five verified official candidates
  into .skillls/ with source/checksum records. No global installation, dependency
  setup, or skill workflow execution was performed.

- [x] Repurposed data/ guidance for account-storage definitions; Snowflake supplies
  candidate JSON directly to the backend. No credentials, database, or login code added.

- [x] Drafted the Snowflake retrieval design in snowflake/PLAN.md on 2026-10-23;
  proposed only. No Snowflake resources, migrations, or code were created.
- [x] Implemented Snowflake retrieval in snowflake/ on 2026-10-23: migrations, Python
  UDF/procedure, ingest scripts, and a key-pair connection runner (scripts/lq.py).
  Local unit tests and synthetic examples removed at the owner's request. Real OSM
  data fetched for Pomona + Claremont (239/244 with parseable hours). Not yet
  deployed to Snowflake; curated places not yet collected.
- [x] Deployed Snowflake retrieval to LOCAL_QUEST_DEV (trial, AWS_US_EAST_2) on 2026-10-23
  with real OSM data for Pomona + Claremont (239 searchable places). Verified live calls,
  backend-role grant, and invalid-input error. Matching is keyword-based because trial
  accounts block Cortex AI functions.
- [x] Moved active Snowflake account to a 120-day trial that allows Cortex (2026-10-23);
  deployed hybrid keyword + AI_EMBED matching (sf_hybrid_v1) and verified live calls.
- [x] Simplified Snowflake to one dataset (Pomona OpenStreetMap, 95 places with hours) on
  2026-10-23; removed Overture, curated overlay, analytics, multi-region, and H3. Hybrid
  keyword + Cortex top-1 fallback matching verified with live calls.
- [x] Matched the API's call LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS(json, address) on 2026-10-23;
  geocoding uses OSM addresses in Snowflake (trial blocks external access). Verified the
  exact call and error cases as LQ_APP_RO; dropped LOCAL_QUEST_DEV.
