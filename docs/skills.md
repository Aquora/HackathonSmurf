# Team skills catalog

Status: restored for team review on October 23, 2026. No skills have been selected
as mandatory, installed, or configured by this document. Developers choose their
component technologies; skill choices should follow those decisions.

## How to use this catalog

Use this file to discuss which skills are useful, who needs them, and whether they
are available in that person's chatbot environment. Actual usage rules live in
[AGENTS.md](../AGENTS.md#skill-selection); read a selected skill's actual SKILL.md
before applying it. A catalog description is not a substitute for its instructions.

“Listed in this session” means the skill appears in the current assistant's skill
catalog. It does not prove availability on teammates' machines, working dependencies,
account access, or successful execution. Entries below are options, not mandates.

## Skills listed in this session

### review-bugbot
- Purpose: review code changes for correctness issues.
- Potential users: backend/frontend contributors and the person integrating changes.
- Consider when: a working increment is ready for review.
- Needs: the review facilities specified by its SKILL.md and readable changes.
- Team decision: undecided.

### review-security
- Purpose: review security-sensitive changes.
- Potential users: backend contributor and integration owner.
- Consider when: implementing session ownership, check-in tokens, business metrics
  access, or model-output handling.
- Needs: supported review facilities and the relevant code/configuration.
- Team decision: undecided.

### deploy-with-vercel
- Purpose: link and deploy a project to Vercel through its supported tools.
- Potential users: the developer responsible for frontend deployment.
- Consider only if: Vercel is selected and deployment is authorized.
- Needs: provider access, project configuration, and compatible application setup.
- Team decision: deferred until hosting is chosen.

### imagegen
- Purpose: generate or edit bitmap artwork, such as illustrations or passport art.
- Potential users: frontend/design contributor.
- Consider when: custom raster assets would improve the interface; ordinary layout
  and code-native icons do not require image generation.
- Needs: the image-generation tools supported by the skill.
- Team decision: optional candidate; undecided.

### skill-installer
- Purpose: install requested skills from a supported source.
- Potential users: teammates who need a skill missing from their environment.
- Consider when: a skill has been selected and its source verified.
- Needs: source access and permission to write to the installation location.
- Team decision: use only if installation is needed; it does not configure accounts.

### skill-creator
- Purpose: create or update a reusable skill.
- Potential users: a contributor maintaining a repeatable team workflow.
- Consider when: an existing skill does not fit and the workflow has been exercised.
- Needs: a clear scope and verified instructions to encode.
- Team decision: deferred; no custom skill is required to start building.

### create-rule
- Purpose: maintain persistent repository guidance.
- Potential users: the person maintaining shared agent instructions.
- Consider when: changing working rules; this repository uses AGENTS.md, so avoid
  duplicating those rules in editor-specific files.
- Team decision: optional maintenance capability; undecided.

### openai-docs
- Purpose: consult current guidance for OpenAI/Codex products and configuration.
- Potential users: teammates working on those products or their agent setup.
- Consider only when: the task actually concerns those products. This does not
  select an OpenAI model or replace the project's open-weight AI requirement.
- Team decision: conditional; undecided.

## Earlier candidates requiring discovery and verification

These names appeared in the earlier catalog, but they are not listed in this
session's available skills. Their current source, contents, installability, and
compatibility have not been checked. Do not treat this as an installation list.

- **playwright**: possible browser-testing workflow for quest generation, check-in,
  passport, narrow-screen behavior, and keyboard navigation. Needs a running app
  and browser environment. Equivalent browser tools or project tests may suffice.
- **render-deploy**: possible backend-deployment workflow, only if Render is selected.
  Needs provider access, verified build/start steps, and a health check.
- **gh-fix-ci**: possible help diagnosing failed GitHub Actions checks, only if that
  CI platform is adopted. Needs repository/check access and reproducible failures.
- **security-best-practices**: possible stack-specific security guidance. Verify
  language/framework support and overlap with existing review capabilities.
- **sentry**: possible error investigation workflow, only if Sentry is selected and
  configured. Needs appropriately scoped access; application logs may suffice.

Team decision for these candidates: undecided; discover and inspect only when needed.

## Capabilities without a selected skill

Snowflake querying, dataset curation, schema validation, and open-weight model
evaluation are important project work. No dedicated skill for these has been
verified here. Contributors may use official documentation, available tools, and
project tests; do not invent skill names or assume an integration is connected.

Context7 is a documentation tool, not a skill. GitHub, browser, Snowflake, and
deployment integrations are also distinct from skills. Credentials and tool access
must be established separately. A testing skill helps run checks but does not
replace the acceptance criteria in [TESTING.md](TESTING.md).

## Team selection record

No team selections have been made yet. When the team decides, add a concise entry:

```text
Skill and verified source:
Decision: selected | optional | deferred | not needed
Purpose and applicable component:
Person/environment that needs it:
Availability checked on:
Required tools/accounts:
Reason for decision:
```

Choose the smallest useful set. Teammates do not need identical skills installed;
they do need to follow the same product requirements and component contracts.
Document source/version when available so others can reproduce a selected setup.
