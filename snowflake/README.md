# Snowflake: top places near the user (Pomona test)

The API makes exactly this call:

```sql
CALL LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS(
  PARSE_JSON('{"desiredTime":120,"desiredBudget":25.0,"locationPreference":"coffee, art","travelMethod":"walk"}'),
  '3801 W Temple Ave, Pomona, CA 91768');
```

Snowflake returns up to 10 Pomona businesses near that address that are **open from
now until `desiredTime` minutes from now**. They are ranked by how well they match
the preferences and how close they are.

**Status (2026-10-23):** deployed to database `LOCAL_QUEST` on account
`LHXLXHN-WY63275` (AWS_US_EAST_2).
- **Loaded:** 97 OpenStreetMap businesses (94 with readable hours) and 1,220 OSM street addresses.
- **Verified as `LQ_APP_RO`:** the exact call above, plus invalid travel method, unknown address, malformed address, and negative budget.
- **Removed:** the earlier `LOCAL_QUEST_DEV` database.
- **Stale:** an earlier account (`YVRSKSP-BQ40898`) still holds an older version.

## Dataset
The only dataset is **OpenStreetMap**, fetched from the Overpass API. It covers
named businesses with an `opening_hours` tag inside Pomona's bounding box
`34.01,-117.83,34.10,-117.71`, which includes Cal Poly Pomona. License: ODbL-1.0.
Show "© OpenStreetMap contributors" wherever the data appears. OSM has no prices,
so `desiredBudget` is validated but not used for filtering.

**Addresses:** the same OSM extract supplies street addresses (house number + street)
to geocode the request's address inside Snowflake. This trial account blocks all
outside network access ("External access is not supported for trial accounts"), so
an online geocoder can't be used. OSM has only about 1,200 addressed places in
Pomona: most businesses and the Cal Poly campus are covered, but most home
addresses are not.

## Layout
| Path | Purpose |
|---|---|
| `sql/01_setup.sql` | Roles `LQ_OWNER`/`LQ_APP_RO`, warehouse `LQ_WH` (XS, 60 s suspend, 10-credit monitor), database, schema `QUEST` |
| `sql/02_tables.sql` | `PLACE`, `PLACE_HOURS`, `INTEREST_SYNONYM` (seeded), `CATEGORY_EMBEDDING`, stages |
| `sql/03_functions.sql` | `PARSE_OSM_HOURS` UDF, `FIND_QUEST_LOCATIONS(VARIANT, STRING)` procedure, backend grant |
| `sql/04_load.sql` | Replace places and addresses from the uploaded NDJSON, parse hours, embed new categories |
| `python/lq_snowflake/` | Procedure code: `request` (API parsing), `addresses` (normalization), `hours`, `ranking`, `procedure`, `osm_hours` (parser), `settings` |
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
$PY $LQ load               # refresh Pomona places + addresses from OSM
$PY $LQ call test.json "3801 W Temple Ave, Pomona, CA 91768"   # --out FILE, --role LQ_APP_RO
```

## Request
Two arguments: the JSON and the address.

| Field | Meaning |
|---|---|
| `desiredTime` | Minutes available, from 1 to 1440 |
| `desiredBudget` | Dollars, at least 0. Validated and echoed, not used for filtering |
| `locationPreference` | Comma-separated preferences, up to 5. May be empty |
| `travelMethod` | Must be `walk` for now |
| address | `"<number> <street>, <city>, <state> <zip>"`, looked up in the OSM addresses |

A bad input fails with `LQ_INVALID_INPUT: <field>: <reason>`. Examples:
- `travelMethod: supported: walk`
- `address: not found in the Pomona address data`
- `desiredBudget: must be a non-negative number of dollars`

## Response
The top level is `{request_id, retrieved_at, ranking_version, constraints, candidate_count, candidates[]}`.

`constraints` shows how Snowflake read the request:
- `address` and `matched_address`
- `start` coordinates
- `departure_time` (now) and `timezone`
- `available_seconds`
- `budget` in cents
- `interests`
- `travel_method`

Each candidate has:
- `rank`, `place_id`, `name`, `tags`
- `coordinates`, `distance_m`, `address`, `website`
- `opening_intervals`, with real open and close times
- `hours_as_of`, `source_url`, `attribution`
- `match_reasons`

Zero candidates is a valid result.

## How results are chosen
1. Geocode the address. Match the house number, normalized street ("W Temple Ave" = "West Temple Avenue"), and ZIP against `APP.ADDRESS`. When several OSM features share the address, use their median point.
2. Businesses within `min(2000 m, 1.3 m/s × desiredTime × 60 / 2)` straight-line distance.
3. Keep only those open for at least 20 continuous minutes between now (Pomona time) and now + `desiredTime`. Unknown hours are excluded, never guessed.
4. Preference match is the best tag score across the preferences:
   - **Keyword:** 1.0 for an exact tag, the weight in `QUEST.INTEREST_SYNONYM` for a synonym (e.g. coffee → cafe 0.9), or 0.8 when the interest is a word in the tag.
   - **Cortex fallback:** used only for interests with no keyword match nearby. `AI_EMBED` finds the single closest category (e.g. "cozy study spot" → cafe), which scores 0.85 if its cosine is at least 0.8. Only the top 1 is used because ranks 2–5 were noise on this data.
5. Score = 0.7 × match + 0.3 × closeness. Ties go to the shorter distance, then `place_id`. The top `limit` are returned.

Settings live in `python/lq_snowflake/settings.py`. Change `RANKING_VERSION`
whenever a setting changes. The synonym table can be edited with `MERGE` without
redeploying.

## Notes
- **Login:** key-pair login uses the *login name* (`ERICY` here; it was the email on the earlier account).
- **Cortex on trials:** some trial accounts block Cortex AI functions entirely. This account allows them.
- **Data gap:** many Cal Poly campus businesses (Saddles Cafe, the library Starbucks, Element Coffee, Lollicup, Panda Express and others) are in OSM without `opening_hours`. The hours rule therefore excludes them, so a campus start finds only about 4 open places within 2 km.
- **Contract impact:** candidates are leaner than the draft TEAM-CONTRACT `PlaceRecord`. They have no cost, visit time, or facts, because OSM doesn't provide them. Agree the shape with the backend owner.
