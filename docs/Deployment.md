# Hackathon deployment checklist

Status: planning checklist. No application, deployment target, commands, URLs, or
rollback procedure have been verified. Fill in the exact steps and record results
as the demo is built. This checklist covers the hackathon demo only.

## Setup
- [ ] Confirm the event deadline, demo URL needs, and who can deploy: [TO FILL]
- [ ] Confirm hosting and service accounts. Vercel (web) and Render (API) are
  earlier suggestions, not selected providers; coordinate hosting with the chosen
  component technologies in `ARCHITECTURE.md`: [TO FILL]
- [ ] Record required environment variable **names and purposes** in example
  configuration; store values in the selected providers' secret settings.
- [ ] Confirm which services and datasets are live, simulated, or unavailable.
  Keep demo activity separate from real merchant metrics and redemptions.
- [ ] Prepare the approved place data, its source/attribution, and a safe demo
  account or session if the journey needs one.
- [ ] Record the selected URL(s), deploying owner/role, and any cost limits:
  [TO FILL]

## Deploy
- [ ] Run the verified install, build, test, and AI evaluation commands recorded
  in `../README.md` and `TESTING.md`; record actual results: [TO FILL]
- [ ] Check configuration and data compatibility. If a schema change is needed,
  document its order and recovery step before applying it: [TO FILL]
- [ ] Deploy the API and web app using the selected provider's verified steps:
  [TO FILL]
- [ ] Record the deployed version/commit, model and prompt versions, deployment
  time, and URL(s): [TO FILL]

## Smoke check
- [ ] Confirm the deployed app loads and the API health check succeeds. Exact
  URL and expected result: [TO FILL]
- [ ] Complete the core journey: enter preferences, review them, generate a
  feasible three-stop quest, inspect route facts, complete a simulated check-in,
  and see the passport and dashboard update.
- [ ] Try an infeasible budget or time request and confirm it gives an honest
  explanation. Check that simulated data and offers are visibly labeled.
- [ ] Confirm no smoke check creates a real merchant redemption. Record the
  browser/device, test data, results, and any failures: [TO FILL]

## Rollback
- [ ] Record a known working deployment/version and how to restore it for each
  selected provider before the demo: [TO FILL]
- [ ] If the deployed journey fails, stop using the broken URL and restore the
  known working version with the provider's verified steps: [TO FILL]
- [ ] If a data or configuration change caused the failure, use only a documented
  recovery step. Record what changed and whether the demo needs a clearly
  labeled fixture or recording instead: [TO FILL]
- [ ] Re-run the health check and core journey after restoration; record the
  result and the version shown to judges: [TO FILL]

## Result
Record who ran this checklist, when, the deployed version, checks that passed,
checks that failed or were skipped, and the demo URL. Do not describe a planned
or simulated step as verified.

## Demo and submission

This is a proposed script, not a claim of working functionality.

### Short demonstration
1. Explain the problem: finding an affordable, interesting short outing takes effort.
2. Enter interests, time, and budget; show editable AI-extracted preferences.
3. Generate a three-stop route from the curated neighborhood catalog.
4. Explain one grounded challenge and its source place fact.
5. Change a constraint and show a feasible new result or honest infeasibility response.
6. Scan a simulated stop QR, earn a passport stamp, and show the analytics update.
7. Identify Snowflake retrieval/analytics and the actual open-weight model used.

### Evidence for prize entries
- Show a real Snowflake query and resulting application behavior.
- Show AI contribution, model identity, license link, and evaluation examples.
- Publish source with a selected open-source license and reproducible setup.
- Label simulated check-ins/offers/data; do not imply merchant partnerships.
- Confirm event eligibility, submission fields/deadline, and permitted advance work.

### Advance-work record
2026-10-22: project documentation prepared from brainstorming. No application code,
verified business dataset, or deployment created by this documentation task.

### Backup
Record a truthful demo video once the live journey works. If live services fail,
label the recording or offline fixture mode instead of presenting it as live.
