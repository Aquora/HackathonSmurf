# Quest API contract (v1)

The route-by-route reference (inputs, outputs, errors, examples) lives in
[api/ROUTES.md](../api/ROUTES.md). Type definitions: `api/app/domain/types.py`.
Machine-readable schema: `GET /openapi.json` on a non-production server.

Quests always start and end at Cal Poly Pomona; the request carries only `message`
(changed 2026-10-23, previously also `location.address`).

This revision uses camelCase fields, dollars, minutes, and miles as requested by the
product owner. It supersedes the snake_case / minor-unit draft in
`docs/TEAM-CONTRACT.md` for this endpoint only.
