# Verification and AI evaluation

Status: planned checks; none have run against an application.

## Shared contract checks
- Validate canonical schemas and all shared message examples once created.
- Check generated client/model representations for drift from the contract.
- Check actual backend responses and frontend consumers against shared examples.
- Verify fixture references, money/time totals, and producer/consumer compatibility.
- Run the connected journey after integrating each slice, not only at final merge.
See TEAM-CONTRACT.md for the proposed contract freeze and acceptance gate.

## Critical behavior
- Valid request yields three unique stops from the retrieved candidate set and a
  consistent route breakdown.
- Omitted duration/budget/interests resolve to 5400 seconds/$30/no preference; valid
  overrides and an explicit zero budget survive normalization. Default currency
  must be configured. Invalid supplied values produce validation errors.
- Responses disclose effective constraints, applied defaults, and defaults version.
  Missing start/time context without an agreed fallback fails explicitly.
- Candidate ranking is stable with tie-breakers, caps at 10, and returns no duplicates;
  fewer than 10 is supported, fewer than three is handled without fabricated stops.
- Default values never replace unknown place hours, coordinates, or costs.
- Walking plus visit durations fit the available time under disclosed estimates.
- Estimated cost fits budget; currency conversion is not silently assumed.
- Arrival and departure fall within opening intervals, including timezone boundaries.
- Impossible budgets, unknown hours, and unavailable paths do not yield false success.
- Request validation rejects malformed coordinates, negative values, and excessive inputs.
- Duplicate/retried check-ins yield one stamp and one logical analytics event.
- Another session cannot read a quest or mutate its check-ins.
- Once authentication is implemented, verify session validation, ownership binding,
  and that responses/logs/repository fixtures contain no password hashes or tokens.
- Generation consumes validated Snowflake JSON without relying on a local catalog
  file or writing candidate responses to data/.
- Business metrics respect owner access and separate simulated activity.

## AI evaluation fixtures
Include vague preferences, contradictory constraints, hostile text in a retrieved
place description, invalid JSON output, invented place IDs, invented discounts,
out-of-candidate-set IDs, duplicate stops, impractical ordering, false cost/time
totals, and provider timeout. Test one repair attempt and exhausted repair. Require
valid schema and approved fact references. Independently calculate feasibility;
model failure must not be reported as proof that no feasible route exists. Record
model identifier/version, prompt version, inputs, expected behavior, and results.
For each case record normalized constraints/default version, candidate/ranking
version, selected order, measured walking time, interest coverage, validation
outcome, number of model/provider calls, and end-to-end latency. Compare against
a small controlled feasible-route baseline within the same candidate set to assess
route quality; do not claim global optimality. Define quality/latency thresholds
after a baseline run; do not invent pass rates.

## End-to-end
Form -> validation/defaults -> Snowflake candidates -> AI proposal -> backend
route verification -> saved quest JSON -> map/cards/default display -> check-in -> passport ->
dashboard, using isolated test data. Include narrow-screen and keyboard navigation
checks and understandable loading/error states.

## Environments
Unit tests use fixtures. Integration tests use dedicated nonproduction resources.
Smoke tests run after deployment and must not create real redemptions. CI should
check types/lint/build, relevant unit/integration checks, and the critical journey.
Record exact verified commands in README when implemented.
