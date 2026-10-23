# Snowflake design note (Pomona test)

Status: implemented and deployed. See [README.md](README.md) for how to run it,
the request/response shape, and the ranking rules.

## Decisions (2026-10-23)
- **Scope:** one dataset, OpenStreetMap, covering Pomona only.
- **Removed:** the earlier multi-source design (Overture Marketplace matching, a
  curated overlay, multi-region ingest, an H3 prefilter, analytics views).
- **Hours are required:** a place is returned only if its OSM `opening_hours`
  parse and show it open for at least 20 minutes during the user's window.
  Unsupported syntax (holidays, sunrise, comments) means unknown, so the place
  is excluded.
- **Matching:** keyword/synonym first. Cortex `AI_EMBED` is a fallback that uses
  only the top-1 closest category per interest. Measured on this data, the
  closest category was right for every probe, and ranks 2–5 were noise.
- **Interface:** the backend calls `QUEST.GET_CANDIDATES(PARSE_JSON(?))` as role
  `LQ_APP_RO`, which can run only that procedure. Request values are bound, never
  concatenated into SQL.
- **Budget:** validated but not used for filtering, because OSM has no prices.

## Open
- The response shape vs. the draft TEAM-CONTRACT `PlaceRecord` (no cost, visit
  time, or facts): agree it with the backend and AI owners.
- About 95 places is small. Widening the bounding box or adding a second source
  is a later decision.
- Event delivery and analytics were removed. Revisit them if the dashboard needs
  Snowflake.
