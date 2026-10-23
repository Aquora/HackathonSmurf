# Snowflake candidate retrieval plan

Status: **implemented in this folder; not yet deployed or run in Snowflake** (see [README.md](README.md)). No Snowflake objects or data loads
exist yet. Field additions marked **contract impact** need agreement
from the integration lead and the backend/AI owners before freeze
(see [TEAM-CONTRACT.md §6](../docs/TEAM-CONTRACT.md)).

## 1. Scope

Snowflake owns:
- the place catalog: Marketplace POIs, OSM opening hours, and the curated overlay
- ranked top‑10 candidate retrieval around the user's location
- analytics views (later phase)

`api/` owns the connector adapter that calls Snowflake and maps the result into the
shared schemas. The browser never talks to Snowflake.

## 2. Confirmed decisions (2026-10-23)

| Topic | Decision |
|---|---|
| Business data | A free Snowflake Marketplace POI dataset (Overture Maps Places, to verify), plus a hand-curated overlay |
| Opening hours | OpenStreetMap `opening_hours` tags parsed in Snowflake. Curated hours override them. |
| Unknown hours | **Excluded.** We never send a user to a place that might be closed. |
| Search center | The user's location (`constraints.start`), which the backend provides. Search is not limited to a fixed neighborhood. |
| Preference matching | Hybrid (`sf_hybrid_v1`): the higher of keyword/synonym matching and Cortex `AI_EMBED` top-k category closeness. Falls back to keywords only (`sf_keyword_v1`) on accounts that block Cortex. |
| Result size | Up to 10 candidates. Fewer is valid, and results are never padded. |
| Interface | The backend calls a stored procedure, which returns one `CandidateSet` VARIANT |

## 3. Workflow

```text
SETUP (batch, before demo)                     REQUEST (per quest)
─────────────────────────                      ─────────────────────────────────────
Marketplace POIs ──► POI_BASE (+H3 cell)       backend
OSM extract ──► OSM_POI ──► PARSE_OSM_HOURS      │ CALL APP.GET_CANDIDATES(PARSE_JSON(?))
        └─► POI_HOURS_MATCH (≤50 m, name ≈)      ▼
Curated overlay ──► PLACE, PLACE_HOURS,        1. validate input
                    PLACE_FACT                 2. H3 prefilter + ST_DWITHIN(start, radius)
Cortex EMBED ──► CATEGORY_EMBEDDING,           3. expand hours → keep open-long-enough
                 PLACE_EMBEDDING               4. budget filter (curated cost known)
                                               5. embed interests, cosine similarity
                                               6. score, dedupe, order, LIMIT 10
                                               7. build CandidateSet VARIANT ──► backend
```

The backend sends the candidates to the AI, which selects and orders three stops.
The backend then verifies the actual walking route, costs, and hours.

## 4. Snowflake objects

Database `LOCAL_QUEST` (demo) with a separate `LOCAL_QUEST_DEV` for development.

### RAW
- Secure views over the Marketplace share.
  - **To verify:** the exact Overture Maps Places listing, its columns, and its license (expected CDLA‑Permissive‑2.0).
  - Fallback: Foursquare OS Places (Apache‑2.0).

### CATALOG

**`POI_BASE`** normalizes the Marketplace places. It is not clipped to a city.
- Columns: `source_id`, `name`, `categories` (ARRAY of normalized labels), `point` (GEOGRAPHY), `h3_r7`, `address`, `website`, `confidence`, `region_id`, `release`.
- `h3_r7 = H3_POINT_TO_CELL(point, 7)`. The table is clustered by `h3_r7` so each lookup touches only nearby cells.
- Loaded only for active `INGEST_REGION` bounding boxes. Search works anywhere inside loaded regions.

**`OSM_POI`** holds OSM nodes and ways that have an `opening_hours` tag.
- Columns: `osm_ref`, `name`, `latitude`, `longitude`, `point`, `h3_r7`, `tags`, `categories`, `opening_hours_raw`, `parsed_hours`, `region_id`, `snapshot_date`.
- Loaded from NDJSON produced by `ingest/osm_fetch.py` (Overpass API, per region) via `ingest/02_load_osm.sql`.
- ODbL requires attribution: "© OpenStreetMap contributors".

**`POI_HOURS_MATCH`** links Overture places to OSM records.
- Match rule `match_v1`: within 50 m (`ST_DWITHIN`), `JAROWINKLER_SIMILARITY(lower(name), lower(osm_name)) ≥ 90`, and the best match per place.
- OSM POIs that have hours but no Overture match are admitted as places with `source = 'osm'`.

**`PLACE_HOURS_WEEKLY`** is the resolved weekly schedule used at request time.
- Columns: `place_id`, `day_of_week` (0 = Monday), `open_minute`, `close_minute` (minutes from local midnight; above 1440 for overnight), `hours_source` (`curated` | `osm`), `raw_text`.
- Curated `PLACE_HOURS` rows take precedence over OSM rows.

**`PARSE_OSM_HOURS(text) → ARRAY`** is a Python UDF.
- It supports day ranges (`Mo-Fr`), lists (`Mo,We`), multiple time ranges, `off`, `24/7`, and overnight spans (`18:00-02:00`).
- Anything else returns `NULL`, which means unknown and therefore excluded. That includes `PH`, sunrise/sunset, comments, week or month selectors, and malformed text.
- The parser is hand-written. Check whether the Snowflake Anaconda channel offers an opening-hours library before adding a dependency.

**Curated overlay**, maintained by the Snowflake owner:
- `PLACE`: `place_id`, `source_id`, `osm_ref`, `business_id` (nullable), `name`, `description`, `tags`, `latitude`, `longitude`, `timezone` (IANA), `visit_seconds`, `estimated_cost_minor`, `currency`, `source_url`, `verified_at`, `publication_rights`, `demo`, `approved`, `updated_at`.
- `PLACE_HOURS`: `place_id`, `day_of_week`, `open_minute`, `close_minute`.
- `PLACE_HOURS_EXCEPTION`: `place_id`, `exception_date`, `open_minute`, `close_minute`, `closed`.

**`PLACE_INDEX`** is the searchable table, rebuilt by `ingest/04_refresh_index.sql`. It holds only places with known hours: approved curated places, Overture places matched to OSM hours, and unmatched OSM places with hours.
- `PLACE_FACT`: `fact_id`, `place_id`, `text`, `source_url`, `verified_at`.

**Embeddings**:
- `CATEGORY_EMBEDDING`: one row per distinct category label, with columns `label`, `embedding VECTOR(FLOAT,768)`, `model`, `embedded_at`. There are roughly 2k labels, so each is embedded once.
- `PLACE_EMBEDDING`: curated places only, with columns `place_id`, `search_doc`, `embedding`, `model`, `embedded_at`. `search_doc` is built from name, tags, categories, and description.

### APP
- `CONFIG`: one active row whose `settings` JSON holds `ranking_version`, `w_sim`, `w_dist`, `w_curated`, `max_radius_m`, `walking_speed_mps`, `min_open_seconds_default`, `min_confidence`, `similarity_threshold`, `limit_cap`, `max_interests`, `pool_size`, `embed_model`, `supported_currencies`.
- `GET_CANDIDATES(request VARIANT) RETURNS VARIANT`: a Python stored procedure (owner's rights). It was chosen over Snowflake Scripting so the hours, validation, and ranking logic can be unit-tested locally. SQL still does the spatial search and Cortex similarity.

### ANALYTICS
- `EVENT_RAW` stores `AnalyticsEvent` rows.
- `EVENT_DEDUP` keeps one row per `event_id`.
- `PLACE_DAILY_METRICS` keeps demo and real activity in separate rows and never equates check-ins with purchases.

## 5. Request-time logic

### 5.1 Validate input
Each check below raises `LQ_INVALID_INPUT: <field>` on failure:
- `limit` is between 1 and 10.
- Latitude is within [-90, 90] and longitude within [-180, 180].
- `departure_time` is ISO 8601 with an offset, and `timezone` is a valid IANA name.
- `available_seconds` > 0.
- `budget.amount_minor` ≥ 0 (zero is valid), and `budget.currency` is supported.
- `interests` is an array of short strings, with a maximum count from CONFIG.

### 5.2 Find nearby places
- `radius_m = min(max_radius_m, walking_speed_mps * available_seconds / 2)`.
- Prefilter by `h3_r7 IN H3_GRID_DISK(H3_POINT_TO_CELL(start, 7), k)`, choosing k so the disk covers `radius_m`.
- Then apply the exact `ST_DWITHIN(point, start, radius_m)` and compute `dist_m = ST_DISTANCE(...)`.
- Drop Marketplace rows below `min_confidence` and rows marked closed.
- The radius is a **shortlist filter only**. Straight-line distance never verifies walking time.

### 5.3 Hard hours rule (all places)
- Expand `PLACE_HOURS_WEEKLY` and curated exceptions into absolute `opens_at`/`closes_at` intervals (ISO 8601 with offset) for the window `[departure_time, departure_time + available_seconds)`.
  - Include the previous day's overnight spans.
  - Use `CONVERT_TIMEZONE` with the place's IANA timezone so DST is handled.
  - Uncurated places use the request `timezone`. This is a documented assumption.
- Keep a place only if one interval gives at least `min_open_seconds` of continuous open time inside the window. That threshold is the place's `visit_seconds`, or `min_open_seconds_default` (proposed 1200 s) when unknown.
- Unknown hours exclude the place, and so does too little open time. Returned candidates therefore never have `null` or `[]` `opening_intervals`.

### 5.4 Tiers and budget
- **`curated`**: the overlay is `approved` and has a known cost in the request currency ≤ budget, `visit_seconds` ≤ `available_seconds`, and facts.
- **`unverified`**: an uncurated place with OSM hours. `estimated_cost: null`, `visit_seconds: null`, `facts: []`, `verified_at: null`. Name, coordinates, and categories come from the dataset as-is.
- Nothing is estimated, padded, or invented for either tier.

### 5.5 Preference matching
- **As implemented:** `sf_hybrid_v1` takes the higher of the keyword score and a semantic score (described in the README); `sf_keyword_v1` uses keywords only. For each place tag and interest, the keyword score is:
  - 1.0 for an exact match
  - the synonym weight from `CATALOG.INTEREST_SYNONYM`
  - 0.8 when the interest is a whole word of the tag

  `sim` is the best score over the place's tags.
- **Semantic score:** raw cosine is not used directly because it is too bunched together for short labels. Curated-place description embeddings are not used yet.
- With empty `interests`, `sim = 0`, so ranking uses distance and the curated boost.
- Interest text is data. It arrives inside the bound VARIANT and is never concatenated into SQL.

### 5.6 Ranking (`ranking_version = "sf_semantic_v1"`)
```text
score = round(w_sim * sim + w_dist * (1 - dist_m / radius_m) + w_curated * is_curated, 6)
```
- Initial weights are 0.6 / 0.3 / 0.1, set in CONFIG and tuned with the eval set.
- `QUALIFY ROW_NUMBER() OVER (PARTITION BY place_id ...) = 1` dedupes.
- Order by `score DESC, dist_m ASC, place_id ASC`, which is deterministic, then `LIMIT :limit`.
- `rank` is assigned 1..n after ordering.

### 5.7 Grounded `match_reasons`
Reasons are generated only from record attributes, never by a model:
- `"tag 'coffee' matches interest 'coffee'"`
- `"tag 'art gallery' similar to 'art' (0.81)"`, only when sim ≥ `similarity_threshold`
- `"~420 m straight-line from start"`
- `"hours from OpenStreetMap as of 2026-10-01"` for unverified places

## 6. Procedure interface

Call from the backend adapter with a bound parameter:
```sql
CALL LOCAL_QUEST.APP.GET_CANDIDATES(PARSE_JSON(?));
```

### Request shape
`{request_id, limit, constraints: {start: {latitude, longitude}, departure_time,
timezone, available_seconds, budget: {amount_minor, currency}, interests,
return_to_start}}`. Run one with `scripts/lq.py call <file.json>` (see README).

**Contract impact:** `verification`, `hours_source`, and `hours_as_of` are additions to
`PlaceRecord`. `verified_at`, `description`, and `visit_seconds` being null for
unverified places also needs agreement. TEAM-CONTRACT §6 says unknown costs cannot
prove a strictly feasible quest. The backend and AI owners must decide whether
unverified places may become stops (for example, shown with an "estimate unknown"
label) or are only used when strict planning is not required.

## 7. Errors

| Situation | Snowflake behavior | Backend mapping (proposal) |
|---|---|---|
| Invalid request | Raises `LQ_INVALID_INPUT: <field>` | `VALIDATION_ERROR` / `INTERNAL_ERROR` (the backend should have caught it first) |
| No eligible places | Success with `candidates: []`, `candidate_count: 0` | `NO_FEASIBLE_ROUTE` with reason "insufficient candidates" |
| 1–2 candidates | Success; the list is not padded | Insufficient candidates for a three-stop quest |
| Cortex, warehouse, or timeout failure | Snowflake error | `DEPENDENCY_UNAVAILABLE` |

An empty successful result and a service error are always distinguishable.

## 8. Backend hand-off (`api/` owner)

- Use the official Snowflake connector for the backend language with key-pair auth and a query timeout.
- Environment variable **names** (values belong in secret storage, never in the repo):
  `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY_PATH`,
  `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`.
- Validate the returned VARIANT against the shared `CandidateSet` schema once it exists in `contracts/`.
- Treat descriptions, facts, and names as untrusted text when passing them to the AI.

## 9. Security and cost

- Role `LQ_APP_RO` has `USAGE` on the database, schema, warehouse, and `GET_CANDIDATES` only, with no table grants. The procedure runs with owner's rights.
- A dedicated service user uses key-pair auth, with no password login.
- An XS warehouse with `AUTO_SUSPEND = 60`, plus a resource monitor with a credit cap.
- Cortex embedding calls are bounded by the per-request interest count limit.
- Dev and demo databases are separate. Tests never run against the demo database silently.

## 10. Folder layout

The layout as built is listed in [README.md](README.md#layout).

## 11. Tests and data-quality checks

**Output shape**
- ≤ 10 candidates, distinct `place_id`, ranks 1..n contiguous, and `candidate_count` equal to the array length.
- Every candidate has provenance (`source_url`, `publication_rights`, `hours_source`, `hours_as_of`).

**Determinism**
- Two identical calls return identical output, except `retrieved_at`.

**Paths**
- No preference, an empty area (success, empty list), invalid input (named error), and zero budget (curated places costing more than 0 are excluded).

**Hours**
- Unknown hours are excluded.
- A place closed at departure that opens later in the window is kept only with enough open time.
- A place closing 5 minutes into the window is excluded.
- Overnight spans (`Fr 18:00-02:00`) and a DST-boundary date (2026-11-01, America/Los_Angeles) are handled.

**Parser**
- A table of OSM strings with expected output, including strings that must return `NULL`.

**Budget and currency**
- The cost filter respects the budget, and a currency mismatch is rejected.

**Relevance eval**
- A small set of interest → expected top places, with the embedding model, ranking version, and results recorded.

**Coverage report**
- The share of POIs in the demo region with parseable hours.

## 12. Milestones

| ID | Deliverable |
|---|---|
| M0 | Account/region checked for Cortex model availability; Marketplace listing and license verified |
| M1 | Catalog schema; 10–15 curated places in the demo area |
| M1b | OSM hours load, `PARSE_OSM_HOURS`, Overture↔OSM matching, and hours coverage report |
| M2 | Category and curated-place embeddings |
| M3 | `GET_CANDIDATES` deployed and checked with real requests |
| M4 | Backend hand-off with schema-checked examples in `contracts/examples/` |
| M5 | Analytics event tables and deduplicated metrics views |

## 13. Open decisions

- Demo area for the curated overlay. Pomona/Claremont is suggested because of the event location; search itself works wherever the dataset has coverage.
- Whether `unverified` places may become quest stops (contract impact, §6).
- H3 resolution, the k value, and the regional materialization for the demo.
- Default currency (USD appears only in examples).
- Cortex model availability in the chosen account region.
- Ranking weights, similarity threshold, and `min_open_seconds_default`.
- OSM and Marketplace refresh cadence.
- Event delivery path into analytics.
