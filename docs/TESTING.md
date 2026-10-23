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
- Valid request yields three unique known stops and a consistent route breakdown.
- Walking plus visit durations fit the available time under disclosed estimates.
- Estimated cost fits budget; currency conversion is not silently assumed.
- Arrival and departure fall within opening intervals, including timezone boundaries.
- Impossible budgets, unknown hours, and unavailable paths do not yield false success.
- Request validation rejects malformed coordinates, negative values, and excessive inputs.
- Duplicate/retried check-ins yield one stamp and one logical analytics event.
- Another session cannot read a quest or mutate its check-ins.
- Business metrics respect owner access and separate simulated activity.

## AI evaluation fixtures
Include vague preferences, contradictory constraints, hostile text in a retrieved
place description, invalid JSON output, invented place IDs, invented discounts,
and provider timeout. Require valid schema and approved fact references. Record
model identifier/version, prompt version, inputs, expected behavior, and results.
Define quality/latency thresholds after a baseline run; do not invent pass rates.

## End-to-end
Form -> preference confirmation -> quest -> map/cards -> check-in -> passport ->
dashboard, using isolated test data. Include narrow-screen and keyboard navigation
checks and understandable loading/error states.

## Environments
Unit tests use fixtures. Integration tests use dedicated nonproduction resources.
Smoke tests run after deployment and must not create real redemptions. CI should
check types/lint/build, relevant unit/integration checks, and the critical journey.
Record exact verified commands in README when implemented.
