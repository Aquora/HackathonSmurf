# Local Quest implementation plan

Current phase: owner-confirmed generation workflow documented; contract details
remain draft and no application implementation exists.

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
- [ ] Create canonical API contracts and synthetic fixtures.
- [ ] Scaffold frontend/backend; verify install/build/test commands in README.
- [ ] Demonstrate a form calling the backend and rendering a labeled fixture quest.

## 3. Parallel implementation after contracts stabilize
- [ ] Frontend worker: form/default display, route map/cards, passport, dashboard UI in web/.
- [ ] Backend/AI worker: normalization, AI candidate selection/order, grounding, verification, persistence in api/.
- [ ] Data worker: curated catalog, ranked top-10 parameterized queries, event views in snowflake/.
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

- [x] Created six main work areas with AGENTS.md contributor guides only; no nested
  source folders, dependencies, application code, or executable tests were added.

- [x] Copied eight existing skills and downloaded five verified official candidates
  into .skillls/ with source/checksum records. No global installation, dependency
  setup, or skill workflow execution was performed.
