# Snowflake: top places near the user (Pomona test)

The backend sends one request JSON. Snowflake returns up to 10 Pomona businesses
near the start point that are **open during the user's time window**, ranked by how
well they match the user's interests and how close they are.

**Status (2026-10-23):** deployed to `LOCAL_QUEST_DEV` on account `LHXLXHN-WY63275`
(AWS_US_EAST_2). It holds 98 OpenStreetMap businesses, 95 of them with readable
hours. Verified with live calls as `LQ_APP_RO`, an invalid `limit`, and a start
outside Pomona (successful empty result). An earlier account (`YVRSKSP-BQ40898`)
still holds an older multi-source version and is stale.

## Dataset
The only dataset is **OpenStreetMap**, fetched from the Overpass API. It covers
named businesses with an `opening_hours` tag inside Pomona's bounding box
`34.01,-117.83,34.10,-117.71`, which includes Cal Poly Pomona. License: ODbL-1.0.
Show "© OpenStreetMap contributors" wherever the data appears. OSM has no prices,
so `budget` is validated but not used for filtering.

## Layout
| Path | Purpose |
|---|---|
| `sql/01_setup.sql` | Roles `LQ_OWNER`/`LQ_APP_RO`, warehouse `LQ_WH` (XS, 60 s suspend, 10-credit monitor), database, schema `QUEST` |
| `sql/02_tables.sql` | `PLACE`, `PLACE_HOURS`, `INTEREST_SYNONYM` (seeded), `CATEGORY_EMBEDDING`, stages |
| `sql/03_functions.sql` | `PARSE_OSM_HOURS` UDF, `GET_CANDIDATES` procedure, backend grant |
| `sql/04_load.sql` | Replace data from the uploaded NDJSON, parse hours, embed new categories |
| `python/lq_snowflake/` | Procedure code: `request` (validation), `hours`, `ranking`, `procedure`, `osm_hours` (parser), `settings` |
| `scripts/lq.py` | Runner: `check`, `setup [--reset]`, `deploy`, `load`, `call` |
| `scripts/osm_fetch.py` | Pomona OSM download (used by `load`) |

## Run
One-time local setup: create `snowflake/.venv` with `snowflake-connector-python`,
then copy `.env.example` to `.env` and fill it in. `.env` is gitignored, and the
key file stays outside the repo.

```sh
PY=snowflake/.venv/bin/python; LQ=snowflake/scripts/lq.py
$PY $LQ check              # connection works
$PY $LQ setup              # add --reset to drop and rebuild the database
$PY $LQ deploy             # after any Python change
$PY $LQ load               # refresh Pomona data from OSM
$PY $LQ call test.json     # prints the result; --out FILE, --role LQ_APP_RO
```

## Request
```json
{"request_id": "abc", "limit": 10,
 "constraints": {"start": {"latitude": 34.0551, "longitude": -117.75},
  "departure_time": "2026-10-24T14:00:00-07:00", "timezone": "America/Los_Angeles",
  "available_seconds": 5400, "budget": {"amount_minor": 3000, "currency": "USD"},
  "interests": ["coffee", "dessert"], "return_to_start": false}}
```
A malformed request fails with `LQ_INVALID_INPUT: <field>: <reason>`.

## Response
`{request_id, retrieved_at, ranking_version, constraints, candidate_count, candidates[]}`.

Each candidate has:
- `rank`, `place_id`, `name`, `tags`
- `coordinates`, `distance_m`, `address`, `website`
- `opening_intervals`, with real open and close times on the day
- `hours_as_of`, the OSM snapshot date
- `source_url`, `attribution`
- `match_reasons`

Zero candidates is a valid result.

## How results are chosen
1. Businesses within `min(2000 m, 1.3 m/s × available_seconds / 2)` straight-line distance of the start.
2. Keep only those open for at least 20 continuous minutes inside `[departure_time, departure_time + available_seconds)`. Unknown hours are excluded, never guessed.
3. Preference match is the best tag score across the interests:
   - **Keyword:** 1.0 for an exact tag, the weight in `QUEST.INTEREST_SYNONYM` for a synonym (e.g. coffee → cafe 0.9), or 0.8 when the interest is a word in the tag.
   - **Cortex fallback:** used only for interests with no keyword match nearby. `AI_EMBED` finds the single closest category (e.g. "cozy study spot" → cafe), which scores 0.85 if its cosine is at least 0.8. Only the top 1 is used because ranks 2–5 were noise on this data.
4. Score = 0.7 × match + 0.3 × closeness. Ties go to the shorter distance, then `place_id`. The top `limit` are returned.

Settings live in `python/lq_snowflake/settings.py`. Change `RANKING_VERSION`
whenever a setting changes. The synonym table can be edited with `MERGE` without
redeploying.

## Notes
- **Login:** key-pair login uses the *login name* (`ERICY` here; it was the email on the earlier account).
- **Cortex on trials:** some trial accounts block Cortex AI functions entirely. This account allows them.
- **Contract impact:** candidates are leaner than the draft TEAM-CONTRACT `PlaceRecord`. They have no cost, visit time, or facts, because OSM doesn't provide them. Agree the shape with the backend owner.
