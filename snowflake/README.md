# Snowflake: top places near the user (Pomona test)

The API makes exactly this call:

```sql
CALL LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS(
  PARSE_JSON('{"desiredTime":120,"desiredBudget":25.0,"locationPreference":"coffee, art","travelMethod":"walk"}'),
  '3801 W Temple Ave, Pomona, CA 91768');
```

Snowflake returns `{"locations": [...]}` with **10** Pomona-area businesses that are
**open from now until `desiredTime` minutes from now**. They are ranked by how well
they match the preferences and how close they are. The API in `api/` consumes this
directly (`DATA_PROVIDER=snowflake`). On 2026-10-23 an end-to-end `POST /v1/quests`
built a quest from these results, using the API's mock AI step.

**Status (2026-10-23):** deployed to database `LOCAL_QUEST` on account
`LHXLXHN-WY63275` (AWS_US_EAST_2).
- **Loaded:** 97 OpenStreetMap businesses (94 with readable hours) and 1,220 OSM street addresses.
- **Verified as `LQ_APP_RO`:** the exact call above (walk and drive), plus unknown address, malformed address, and negative budget.
- **Removed:** the earlier `LOCAL_QUEST_DEV` database.
- **Stale:** an earlier account (`YVRSKSP-BQ40898`) still holds an older version.

## Dataset
The only dataset is **OpenStreetMap**, fetched from the Overpass API. It covers
named businesses with an `opening_hours` tag inside Pomona's bounding box
`34.01,-117.83,34.10,-117.71`, which includes Cal Poly Pomona. License: ODbL-1.0.
Show "© OpenStreetMap contributors" wherever the data appears.

**Costs:** OSM has no prices, but the API needs a cost per stop to enforce the budget.
Each place therefore gets a **category estimate** from `APP.CATEGORY_COST`, the
highest typical spend among its tags (e.g. cafe $6, pizza $14, museum $10, library
$0). It is returned as `estimatedCost`, with `costBasis` stating that it is a
category estimate, not the place's price. Categories with no sensible visit spend
(car repair, storage, banks, phone shops) have no estimate, so `estimatedCost` is
null and the API won't use them as stops. The table can be edited with `MERGE`.

**Addresses:** the same OSM extract supplies street addresses (house number + street)
to geocode the request's address inside Snowflake. This trial account blocks all
outside network access ("External access is not supported for trial accounts"), so
an online geocoder can't be used. OSM has only about 1,200 addressed places in
Pomona: most businesses and the Cal Poly campus are covered, but most home
addresses are not.

## Layout
| Path | Purpose |
|---|---|
| `sql/01_setup.sql` | Roles `LQ_OWNER`/`LQ_APP_RO`, warehouse `LQ_WH` (XS, 60 s suspend, 10-credit monitor), database, schema `APP` |
| `sql/02_tables.sql` | `PLACE`, `PLACE_HOURS`, `ADDRESS`, `INTEREST_SYNONYM` and `CATEGORY_COST` (seeded), `CATEGORY_EMBEDDING`, stages |
| `sql/03_functions.sql` | `PARSE_OSM_HOURS` UDF, `FIND_QUEST_LOCATIONS(VARIANT, STRING)` procedure, backend grant |
| `sql/04_load.sql` | Replace places and addresses from the uploaded NDJSON, parse hours, embed new categories |
| `python/lq_snowflake/` | Procedure code: `request` (API parsing), `addresses` (normalization), `hours`, `ranking`, `procedure`, `osm_hours` (parser), `settings` |
| `scripts/lq.py` | Runner: `check`, `setup [--reset]`, `deploy`, `load`, `call` |
| `scripts/osm_fetch.py` | Pomona OSM download (used by `load`) |

## Run
One-time local setup: create `snowflake/.venv` with `snowflake-connector-python`.
Configuration lives in the project's single `local-quest/.env`, shared with the API
(template: `local-quest/.env.example`). It is gitignored, and the key file stays
outside the repo.

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
| `desiredBudget` | Dollars, at least 0. Echoed; the API checks it against `estimatedCost` |
| `locationPreference` | Comma-separated preferences, up to 5. May be empty |
| `travelMethod` | `walk`, `bike`, `transit`, or `drive` sets the search radius; anything else searches as walk |
| address | `"<number> <street>, <city>, <state> <zip>"`, looked up in the OSM addresses |

A bad input fails with `LQ_INVALID_INPUT: <field>: <reason>`. Examples:
- `address: not found in the Pomona address data`
- `desiredBudget: must be a non-negative number of dollars`

## Response
The top level is `{request_id, retrieved_at, ranking_version, constraints, location_count, locations[]}`.

`constraints` shows how Snowflake read the request:
- `address` and `matched_address`
- `start` coordinates
- `departure_time` (now) and `timezone`
- `available_seconds`
- `budget` in cents
- `interests`
- `travel_method` and `radius_travel_method`

Each location has the fields the API reads, plus extras it ignores:
- **Read by the API:** `name`, `address`, `closingTime` ("HH:MM" local; after midnight means late night), `estimatedCost`
- **Extras:** `rank`, `place_id`, `costBasis`, `tags`, `coordinates`, `distance_m`, `within_radius`, `website`, `opening_intervals`, `hours_as_of`, `source_url`, `attribution`, `match_reasons`

When OSM has no street address, `address` is the coordinates, e.g. `"34.057978, -117.749360"`.

## How results are chosen
1. Geocode the address. Match the house number, normalized street ("W Temple Ave" = "West Temple Avenue"), and ZIP against `APP.ADDRESS`. When several OSM features share the address, use their median point.
2. Businesses within the travel radius, `min(cap, speed × desiredTime × 60 / 2)` straight-line distance:

   | Method | Speed | Cap |
   |---|---|---|
   | walk | 1.3 m/s | 2 km |
   | bike | 4 m/s | 6 km |
   | transit | 6 m/s | 8 km |
   | drive | 11 m/s | 15 km |
3. Keep only those open for at least 20 continuous minutes between now (Pomona time) and now + `desiredTime`. Unknown hours are excluded, never guessed.
4. Preference match is the best tag score across the preferences:
   - **Keyword:** 1.0 for an exact tag, the weight in `APP.INTEREST_SYNONYM` for a synonym (e.g. coffee → cafe 0.9), or 0.8 when the interest is a word in the tag.
   - **Cortex fallback:** used only for interests with no keyword match nearby. `AI_EMBED` finds the single closest category (e.g. "cozy study spot" → cafe), which scores 0.85 if its cosine is at least 0.8. Only the top 1 is used because ranks 2–5 were noise on this data.
5. Score = 0.7 × match + 0.3 × closeness. Ties go to the shorter distance, then `place_id`.
6. The API needs exactly 10. If fewer than 10 open places are inside the radius, the rest are filled from farther open places, up to 25 km, ranked by score then distance. These are marked `within_radius: false` with a match reason saying so. Nothing is invented; the API's route check still enforces the time limit.

Settings live in `python/lq_snowflake/settings.py`. Change `RANKING_VERSION`
whenever a setting changes. The synonym table can be edited with `MERGE` without
redeploying.

## Notes
- **Login:** key-pair login uses the *login name* (`ERICY` here; it was the email on the earlier account).
- **Cortex on trials:** some trial accounts block Cortex AI functions entirely. This account allows them.
- **Data gap:** many Cal Poly campus businesses (Saddles Cafe, the library Starbucks, Element Coffee, Lollicup, Panda Express and others) are in OSM without `opening_hours`. The hours rule excludes them, so a campus walk start finds only about 4 open places within 2 km and fills the rest from farther away.
- **Fewer than 10 open places:** late at night the whole dataset may have fewer than 10 open places. Snowflake then returns fewer, and the API responds `502 UPSTREAM_INVALID_RESPONSE` ("expected exactly 10").
