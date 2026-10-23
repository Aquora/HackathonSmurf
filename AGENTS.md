# Project agent instructions

## Purpose
Use this repository to develop the product described in `PROJECT.md` through a
verified hackathon demo. These instructions apply to the Local Quest folder. All document and code paths
below are relative to this folder, not the parent reusable starter.

## Read before working
- Read `PROJECT.md` for product requirements and `docs/ARCHITECTURE.md` for
  technology ownership. Component developers choose their languages and frameworks
  within shared contracts; coordinate choices affecting other teams or deployment.
- Read `docs/ARCHITECTURE.md` before structural or interface changes.
- Read `docs/PLAN.md` for the current phase, dependencies, and task ownership.
- Read `docs/TEAM-CONTRACT.md` for proposed interfaces and data requirements.
  Draft proposals are not approved schemas; team ownership is in ARCHITECTURE.md.
- Consult `docs/skills.md` for the team catalog and selection status. Project-local
  skill copies are in `.skillls/<name>/SKILL.md`; read only relevant skills.
  Copies do not guarantee native registration, tool access, or configured dependencies.
- Follow the skill-selection guidance below and read the selected skill's actual
  `SKILL.md` before applying it.
- Read `docs/Deployment.md` before hackathon deployment or migration work.
- Follow applicable directory-specific instructions when present.

## Interpret configuration honestly
- `[TO FILL]` and `Undecided` are missing information, not requirements.
- Proposed technology is not confirmed technology. Required, preferred, and
  optional describe selection strength; proposed and confirmed describe status.
- Resolve decisions that materially affect scope, cost, security, or architecture
  with the user. Make and record reasonable assumptions for reversible details.
- Continue independent work while waiting for necessary information.
- Do not invent commands, credentials, deployed services, test results, or data.
- A new product brief does not authorize deleting existing implementation.

## Bootstrap and architecture
1. Inspect existing files and repository state before editing.
2. Establish the product's core journey, release target, and required integrations.
3. Record architecture, component responsibilities, data flow, and open decisions
   in `docs/ARCHITECTURE.md` before substantial implementation.
4. Define shared request/response schemas, error behavior, and representative
   examples before independent components are built in parallel.
5. Plan a minimal end-to-end working slice in `docs/PLAN.md`.
6. Scaffold only the components the confirmed architecture needs.
7. Verify install, development, build, and test commands; record them in the README.

Bootstrap is a phase, not a task to repeat on every request. Maintain the existing
architecture after bootstrap. Update affected documents when decisions change.

## Baseline directory conventions
- `web/`: frontend application and its local tests.
- `api/`: backend, business logic, integrations, and its local tests.
- `contracts/`: authoritative API contracts and shared examples.
- `snowflake/`: Snowflake schema changes and queries, when selected.
- `data/`: small redistributable fixtures, with sources and license information.
- `docs/`: architecture, contracts, plan, testing, and deployment/demo guidance.
- `tests/e2e/`: complete user-journey checks, when applicable.

These are conventions, not a request to create empty directories or unnecessary
services. Record justified deviations in the architecture. Keep one authoritative
definition of each contract and derive other representations where practical.

## Implementation workflow
- Deliver small, working increments with explicit acceptance criteria.
- Use the selected framework's current official documentation; use Context7 when
  available and suitable, otherwise consult primary documentation directly.
- Keep domain logic separate from external service adapters so tests can use
  controlled fixtures. Label mock and demo modes visibly.
- Preserve existing user changes. Avoid unrelated refactoring.
- Update contract consumers and relevant tests when interfaces change.
- Record consequential decisions and their rationale in the architecture.

## Multi-agent coordination
Parallel delegation is authorized for independent implementation, research,
testing, or review within the user's active task. Do not delegate merely to fill
slots, and do not create separate user-owned chats without a user request.
- The lead agent owns integration, shared contracts, and cross-component decisions.
- Give each worker a goal, allowed files, dependencies, and acceptance checks.
- Use separate worktrees/branches for concurrent implementation where available;
  explicitly assign paths. Subagents do not automatically receive isolated files.
- If sharing a checkout, assign disjoint files and coordinate shared changes.
- Respect available concurrency. Use independent review after implementation
  rather than requiring a fixed number of agents on every task.
- Hand off changed files, checks/results, assumptions, and unresolved issues.
- Integrate and verify regularly; do not defer all integration until the end.

## Verification
- Run checks appropriate to the change and required repository checks.
- Test important behavior: validation, authorization, persistence, failure handling,
  and complete user journeys. Avoid tests that only repeat implementation details.
- For AI features, keep repeatable evaluation cases for groundedness, schema
  validity, task success, and relevant failure modes. Re-run affected cases after
  prompt/model changes and record the model/version and results.
- Report checks not run and why. Never describe mocked behavior as live integration.

## Data and security boundaries
- Keep secrets out of source, browser bundles, logs, fixtures, and agent handoffs.
- Document variable names and purposes in example configuration, not real values.
- Enforce authorization and validate input on the server.
- Treat model output and retrieved content as untrusted data. Validate outputs
  before using them for database changes or other actions.
- Use parameterized queries and least-privilege service credentials.
- Separate development, staging, and production data/configuration.
- Use versioned schema changes; document compatibility and recovery before applying
  migrations. Never silently run tests against production.
- Document data sources, permitted use, retention, and deletion when relevant.

## Hackathon deployment discipline
- Follow the selected demo target and `docs/Deployment.md`.
- Use deployment skills only for the configured provider and authorized action.
- Prepare checks and reviewable changes before requesting any needed approval;
  do not repeatedly ask for authorization already granted.
- A deployment is complete only after health checks and relevant smoke tests pass.
- Instructions are not enforcement: implement required CI checks and deployment
  permissions in the actual platform configuration.

## Completion report
Summarize what changed, verification performed, limitations, and any release or
migration implications. Distinguish a working local demo from a deployed demo
that passed smoke checks. Update the plan and affected documentation before handoff.

## Local Quest-specific rules
- Use docs/TEAM-CONTRACT.md and docs/TESTING.md when designing contracts or data.
- Backend normalizes omitted inputs to the configured defaults: 90 minutes, $30,
  and no preference. Preserve valid overrides; reject invalid supplied values.
- Snowflake returns up to 10 candidates; AI selects/orders only those candidate IDs.
  Validate budget, walking duration, opening windows, and place IDs in code before
  saving or returning a quest. Never treat model-generated totals as verification.
- Ground AI challenges in approved facts; never invent discounts or partnerships.
- Keep simulated check-ins and offers distinct from real merchant redemptions.
- This documentation request does not authorize starting application implementation.

## Skill selection

- Select skills by the current task, chosen component technology, and confirmed
  provider. Check the live catalog; historical availability is not proof of access.
- Read the actual SKILL.md and check dependencies and permissions before use.
  Skills do not grant credentials or authorize implementation or deployment.
- If unavailable, report it and use current primary documentation or available tools;
  never claim to have run a missing skill. For necessary installation, verify the
  source and follow the skill-installer workflow. Review third-party instructions.
- Tools and skills are distinct. Use Context7 for current framework documentation
  when suitable; verify connector authentication and permissions independently.
- Keep guidance in AGENTS.md rather than duplicating editor-specific rules. Do not
  create custom skills when an existing workflow fits. A reusable deployment skill
  should follow an actually verified procedure, not speculative commands.
- Browser checks cover quest generation and passport completion. Security review
  covers ownership, merchant metrics, token replay, and model-generated content.
  Deployment skills apply only to selected providers and authorized release work.
- Required checks and permissions must exist in CI/platform settings; documentation
  alone does not enforce them. Avoid machine-specific paths in shared guidance.
