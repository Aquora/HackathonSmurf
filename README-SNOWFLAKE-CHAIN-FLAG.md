# Snowflake chain flag: apply and test (for the Snowflake account owner)

**Who runs this:** whoever has the `LQ_OWNER` key-pair login for Snowflake account
`LHXLXHN-WY63275` (currently Eric). Everything here runs on that machine.
**Branch:** `snowflake-chain-flag`
**Time:** about 5 minutes. Uses a few Cortex credits during `load` (new category labels only).

## What changed

Every place in `LOCAL_QUEST.APP.PLACE` gets a chain label. **Nothing is filtered yet:**
`FIND_QUEST_LOCATIONS` returns the same places as before.

| New column | Meaning |
|---|---|
| `brand` | OSM `brand` tag, e.g. `Starbucks` |
| `brand_wikidata` | OSM `brand:wikidata` tag, e.g. `Q37158` |
| `is_chain` | `TRUE` if any rule below matched |
| `chain_reason` | `brand_tag`, `brand_name`, `repeated_name`, or `NULL` |

Rules, strongest first (names compared lowercase without punctuation or spaces):
1. `brand_tag`: the place has an OSM `brand` or `brand:wikidata` tag.
2. `brand_name`: its name matches another place's brand (an untagged chain location).
3. `repeated_name`: the same name appears at more than one place.

Files: `snowflake/scripts/osm_fetch.py` (keeps the brand tags), `snowflake/sql/02_tables.sql`
(new columns, added in place with `ADD COLUMN IF NOT EXISTS`), `snowflake/sql/04_load.sql`
(sets the label after loading places). Details: `snowflake/README.md` → "Chains".

Already checked (without Snowflake): the same `UPDATE` statement was run in SQLite against a
fresh Pomona OSM download, and both SQL files split into statements correctly with the
connector's own splitter. **Not yet run on Snowflake.** That's this step.

## Steps

From the repository root, with your usual `.env` (owner key-pair login):

```sh
git fetch origin
git switch snowflake-chain-flag
PY=snowflake/.venv/bin/python; LQ=snowflake/scripts/lq.py

$PY $LQ check     # 1. connection works
$PY $LQ setup     # 2. adds the 4 columns; existing rows untouched. Do NOT add --reset.
$PY $LQ load      # 3. re-downloads Pomona OSM, reloads places, sets is_chain
```

`load` replaces the place data with a fresh OpenStreetMap download, as it always does, so
counts may differ slightly from the current data. Its last output line should now include a
`CHAIN_PLACES` column.

## Check the result

Run in a Snowflake worksheet (role `LQ_OWNER`, database `LOCAL_QUEST`):

```sql
-- Expect roughly: brand_tag ~50, NULL ~45, brand_name and repeated_name 0 or a few.
SELECT chain_reason, COUNT(*) FROM LOCAL_QUEST.APP.PLACE GROUP BY 1 ORDER BY 2 DESC;

-- Spot-check: chains should be names like McDonald's, Subway, Starbucks, Target;
-- local ones like Pomona Public Library, Some Crust Bakery, Tavos Tacos.
SELECT name, brand, chain_reason FROM LOCAL_QUEST.APP.PLACE WHERE is_chain ORDER BY name LIMIT 25;
SELECT name FROM LOCAL_QUEST.APP.PLACE WHERE NOT is_chain ORDER BY name LIMIT 25;

-- No place should be left unlabeled (expect 0).
SELECT COUNT(*) FROM LOCAL_QUEST.APP.PLACE WHERE is_chain IS NULL;
```

Then confirm the API's call still works exactly as before (10 locations back):

```sh
echo '{"desiredTime":120,"desiredBudget":25.0,"locationPreference":"coffee, art","travelMethod":"drive"}' > /tmp/lq_test.json
$PY $LQ call /tmp/lq_test.json "3801 W Temple Ave, Pomona, CA 91768" --role LQ_APP_RO
```

Expected numbers above come from the 2026-10-23 extract: 51 of 97 places had a brand tag.

## If something goes wrong

- `setup` fails on `ALTER TABLE`: send the error. Nothing else is changed by it.
- `load` fails partway: places are reloaded inside one transaction, so a failure leaves the
  old data in place. Send the output.
- To remove the columns entirely:
  `ALTER TABLE LOCAL_QUEST.APP.PLACE DROP COLUMN brand, brand_wikidata, is_chain, chain_reason;`
  Running `load` from `main` afterwards restores the previous behavior.

## Report back

Post in the team chat: the `chain_reason` counts, any place you think is labeled wrong, and
whether the `call` check returned 10 locations. Then merge `snowflake-chain-flag` into `main`
(or open a PR for it).

---

## Also, separate and optional: give Dylan's machine read-only API access

Dylan's local API can't reach Snowflake because it has no login on this account. This creates
a service user that only works with a key that lives on Dylan's machine. It has no password and
uses the existing read-only `LQ_APP_RO` role, which can only call `FIND_QUEST_LOCATIONS` and
Cortex `AI_COMPLETE`. The key below is the **public** half, safe to share. Run as an admin:

```sql
USE ROLE SECURITYADMIN;
CREATE USER IF NOT EXISTS LQ_API_DYLAN
  TYPE = SERVICE
  DEFAULT_ROLE = LQ_APP_RO
  DEFAULT_WAREHOUSE = LQ_WH
  COMMENT = 'Local Quest API (Dylan local dev), key-pair only';
ALTER USER LQ_API_DYLAN SET RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzfUJNk6Elw/MJCQNbukjnJjus/msNSUAH+T8J8rcv8NxZzIX+TmSNZZUT9ksKxBZ3km3d/dwcAcL7/WTYngY8lIZ4h7Fk6TMgGhyV04/zJuNDONMYaCAK36Ts0/XSIFTaPVyVRN5bXSQL0jmkJ+MIcjik1hNjcsNHi8Pk7LhG/TE71EebVuECe0pJyV9GHTBFuItUpLctxTffZ6STTssEhRvnq6OvqhY28jy5YWA54QKM/3N7eaefGAScCFJsqKMW6R7R7YHhG/LAxudh8sX6jRPuB4FrTt1+7204w1zAAoeGU0BX2TEAY47jfVoAcPWIVP2WGo/voCl4DHij3VFfQIDAQAB';
GRANT ROLE LQ_APP_RO TO USER LQ_API_DYLAN;
-- Revoke any time: DROP USER LQ_API_DYLAN;
```

Tell Dylan when it's done. On his machine, root `.env` then uses
`SNOWFLAKE_USER=LQ_API_DYLAN` and `SNOWFLAKE_PRIVATE_KEY_PATH=/Users/dylanroman/.snowflake/lq_api_rsa_key.p8`.
