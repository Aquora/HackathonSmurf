# Snowflake: nearby-business candidates

Implements [PLAN.md](PLAN.md). The backend calls one stored procedure with the
user's location, time window, budget, and interests. The procedure returns up to
10 ranked nearby businesses that are **known to be open** during the window, as
`CandidateSet` JSON.

**Status (2026-10-23):** deployed to `LOCAL_QUEST_DEV` on two accounts, both AWS_US_EAST_2:
- **Active:** the 120-day trial `LHXLXHN-WY63275`, login `ERICY`, running `sf_hybrid_v1`.
- **Earlier:** the trial `YVRSKSP-BQ40898`, which blocks Cortex, running `sf_keyword_v1`.

Both hold real OpenStreetMap data for Pomona + Claremont: 244 businesses, 239 of
them (98%) with readable hours, all searchable. Live calls as `LQ_APP_RO` return 10
open, ranked candidates. Not loaded yet: Overture data and curated places.

**Preference matching** takes the higher of two scores for each place tag and interest:
- **Keyword:**
  - exact tag: 1.0
  - synonym in `CATALOG.INTEREST_SYNONYM`: its weight
  - interest as a whole word of a tag: 0.8
- **Semantic** (only when the active config sets `embed_model`): Cortex `AI_EMBED` ranks
  every category by similarity to the interest. The top 5, if above cosine 0.8, score
  0.85, 0.81, and so on. Ranking by closeness instead of raw cosine is deliberate:
  raw scores for short labels are bunched together. Measured on 2026-10-23: related
  pairs score about 0.86–0.93, unrelated about 0.75–0.85, and dessert/pizza scores 0.85.

`setup` checks whether `AI_EMBED` works and activates `sf_hybrid_v1` only if it does.
Otherwise `sf_keyword_v1` stays active. `refresh` embeds only new category labels.

## Layout

| Path | Purpose |
|---|---|
| `migrations/V001…V004` | Roles/warehouse/database, catalog tables, ranking config and stages, analytics views |
| `app/functions.sql` | `APP.PARSE_OSM_HOURS` UDF, `APP.GET_CANDIDATES` procedure, backend grant |
| `python/lq_snowflake/` | Python behind the UDF and procedure (parser, hours, validation, ranking, handler) |
| `ingest/01…04` | Load Overture POIs → load OSM hours → load curated overlay → rebuild index and embeddings |
| `ingest/osm_fetch.py` | Download named OSM businesses with `opening_hours` for one region (Overpass API) |
| `ingest/curated/*.csv` | Curated overlay templates (headers only; fill with verified data) |
| `scripts/lq.py` | Runner: connects with key-pair auth and runs setup, deploy, loads, and `call` |
| `scripts/build_package.py` | Builds `build/lq_snowflake.zip` for the stage |
| `.env.example` | Connection variable names; copy to `.env` (gitignored) |

## Connect and run

One-time local setup (verified 2026-10-23; installs `snowflake-connector-python` 5.1.0):

```sh
python3 -m venv snowflake/.venv
snowflake/.venv/bin/pip install snowflake-connector-python
cp snowflake/.env.example snowflake/.env   # then fill it in
```

First run, from the `local-quest` folder. These steps have not been run against an
account yet:

```sh
PY=snowflake/.venv/bin/python; LQ=snowflake/scripts/lq.py
$PY $LQ check                                   # connection works
$PY $LQ setup                                   # roles, LQ_WH, LOCAL_QUEST_DEV, tables, config
$PY $LQ deploy                                  # UDF + GET_CANDIDATES
$PY $LQ region --id pomona_claremont --bbox 34.02,-117.80,34.14,-117.68
$PY $LQ load-osm --region pomona_claremont      # real OSM businesses + hours
$PY $LQ load-overture --table OVERTURE_MAPS__PLACES.CARTO.PLACE   # optional; needs the Marketplace listing
$PY $LQ load-curated                            # optional; your verified places
$PY $LQ refresh                                 # index + Cortex embeddings
$PY $LQ call path/to/test.json                  # prints the CandidateSet
```

`call --role LQ_APP_RO` runs as the backend role, which proves the grant works.
Re-run `deploy` after any Python change, and `refresh` after any load. Without
Overture, the search uses OSM businesses only, which is fine for a first run.

### Learned on first deploy
- **Login:** key-pair login must use the *login name*. On the first account that's the email, not the lowercase, case-sensitive user name `ericyangwastaken`, which SQL must quote. On the second account it's `ERICY`. Trial accounts may block all Cortex AI functions; the second account allows them.
- **Packages:** runtime 3.11 with `snowflake-snowpark-python` and `tzdata` works. `python-tzdata` is rejected.
- **Statement syntax:** `COMMENT` must precede `RUNTIME_VERSION` in `CREATE FUNCTION`, and `EXECUTE AS` in `CREATE PROCEDURE`.
- **Still unverified:** the Overture table name, its columns, and its license. `ingest/01` assumes `OVERTURE_MAPS__PLACES.CARTO.PLACE`.

## Backend access

The backend (`api/` owner) connects as a dedicated service user with role
`LQ_APP_RO`. That role can only call the procedure. Create the user with
key-pair authentication; only an admin does this, never in a committed file:

```sql
CREATE USER IF NOT EXISTS LQ_BACKEND TYPE = SERVICE DEFAULT_ROLE = LQ_APP_RO
    DEFAULT_WAREHOUSE = LQ_WH RSA_PUBLIC_KEY = '<public key>';
GRANT ROLE LQ_APP_RO TO USER LQ_BACKEND;
```

Backend configuration variable names (store the values only in secret storage):
`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY_PATH`,
`SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`.

Call with a bound parameter and a timeout:

```sql
CALL APP.GET_CANDIDATES(PARSE_JSON(?));   -- bind the request JSON string
```

| Outcome | What the backend sees |
|---|---|
| Success | One VARIANT `CandidateSet` with 0–10 candidates. An empty list means a successful search with no matches. |
| Bad request | Error message starting with `LQ_INVALID_INPUT: <field>: <reason>` |
| Bad/missing config | `LQ_CONFIGURATION_ERROR: …` → map to `CONFIGURATION_ERROR` |
| Warehouse/Cortex failure | Snowflake error → map to `DEPENDENCY_UNAVAILABLE` |

## Data rules
- Only places with known, parseable hours are searchable. A place must stay open long enough during the window: its visit length, or 20 minutes by default.
- `curated` places have verified cost, visit length, and facts. `unverified` places are dataset businesses with OSM hours. Their cost, visit length, and facts are `null`/`[]` and are never estimated.
- OSM data requires the attribution "© OpenStreetMap contributors" wherever it is shown.
- Interest text is always a bound value. The only interpolated SQL value is the embedding model name from `APP.CONFIG`, which is checked against a strict pattern.
