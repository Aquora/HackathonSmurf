-- Tables for the single OpenStreetMap dataset (Pomona). Run as LQ_OWNER with
-- $lq_db set (scripts/lq.py setup).

USE ROLE LQ_OWNER;
USE DATABASE IDENTIFIER($lq_db);
USE SCHEMA APP;

-- OSM businesses (named, with an opening_hours tag). Reloaded by sql/04_load.sql.
CREATE TABLE IF NOT EXISTS PLACE (
    place_id           STRING NOT NULL PRIMARY KEY,   -- 'osm_node_123'
    osm_ref            STRING NOT NULL,               -- 'node/123'
    name               STRING NOT NULL,
    tags               ARRAY,                         -- normalized categories, e.g. 'coffee shop'
    latitude           FLOAT NOT NULL,
    longitude          FLOAT NOT NULL,
    point              GEOGRAPHY NOT NULL,
    address            STRING,
    website            STRING,
    opening_hours_raw  STRING,
    snapshot_date      DATE NOT NULL,
    brand              STRING,                        -- OSM brand tag, e.g. 'Starbucks'
    brand_wikidata     STRING,                        -- OSM brand:wikidata, e.g. 'Q37158'
    is_chain           BOOLEAN,                       -- set by sql/04_load.sql
    chain_reason       STRING                         -- why: brand_tag | brand_name | repeated_name
);
-- Columns added after the first deployment (no-op on new tables).
ALTER TABLE PLACE ADD COLUMN IF NOT EXISTS brand STRING;
ALTER TABLE PLACE ADD COLUMN IF NOT EXISTS brand_wikidata STRING;
ALTER TABLE PLACE ADD COLUMN IF NOT EXISTS is_chain BOOLEAN;
ALTER TABLE PLACE ADD COLUMN IF NOT EXISTS chain_reason STRING;

-- Parsed weekly hours; places with unparseable hours have no rows and are never returned.
-- Minutes from local midnight; close may exceed 1440 for overnight; day 0 = Monday.
CREATE TABLE IF NOT EXISTS PLACE_HOURS (
    place_id      STRING NOT NULL,
    day_of_week   NUMBER NOT NULL,
    open_minute   NUMBER NOT NULL,
    close_minute  NUMBER NOT NULL
);

-- OSM street addresses in Pomona, used to geocode the API's address (this trial
-- account cannot call outside geocoders). street_core is normalized by
-- lq_snowflake.addresses.street_core, e.g. 'West Temple Avenue' -> 'temple ave'.
CREATE TABLE IF NOT EXISTS ADDRESS (
    osm_ref        STRING NOT NULL,
    housenumber    STRING NOT NULL,
    street         STRING NOT NULL,
    street_core    STRING NOT NULL,
    postcode       STRING,
    latitude       FLOAT NOT NULL,
    longitude      FLOAT NOT NULL,
    snapshot_date  DATE NOT NULL
);

-- Keyword matching: interest -> category label with a weight below 1.0.
CREATE TABLE IF NOT EXISTS INTEREST_SYNONYM (
    interest  STRING NOT NULL,
    label     STRING NOT NULL,
    weight    FLOAT NOT NULL
);

MERGE INTO INTEREST_SYNONYM t
USING (
    SELECT column1 AS interest, column2 AS label, column3 AS weight FROM VALUES
    ('coffee', 'cafe', 0.9), ('coffee', 'coffee shop', 0.9), ('coffee', 'tea', 0.7),
    ('tea', 'cafe', 0.8), ('tea', 'bubble tea', 0.9),
    ('boba', 'bubble tea', 0.9), ('boba', 'tea', 0.8),
    ('art', 'art gallery', 0.9), ('art', 'gallery', 0.9), ('art', 'arts centre', 0.9),
    ('art', 'art shop', 0.85), ('art', 'museum', 0.75), ('art', 'craft shop', 0.75),
    ('art', 'frame shop', 0.7),
    ('museum', 'gallery', 0.8), ('history', 'museum', 0.9), ('history', 'memorial', 0.85),
    ('history', 'monument', 0.85), ('history', 'attraction', 0.7),
    ('books', 'books shop', 0.9), ('books', 'library', 0.85), ('books', 'second hand shop', 0.6),
    ('reading', 'books shop', 0.85), ('reading', 'library', 0.9),
    ('music', 'music shop', 0.9), ('music', 'musical instrument shop', 0.85),
    ('music', 'nightclub', 0.6), ('music', 'theatre', 0.7),
    ('food', 'restaurant', 0.9), ('food', 'fast food', 0.85), ('food', 'food court', 0.85),
    ('food', 'cafe', 0.7), ('food', 'bakery shop', 0.75),
    ('restaurant', 'fast food', 0.7), ('restaurant', 'food court', 0.7),
    ('dessert', 'ice cream', 0.9), ('dessert', 'bakery shop', 0.85),
    ('dessert', 'confectionery shop', 0.85), ('dessert', 'pastry shop', 0.9),
    ('dessert', 'donut', 0.85), ('dessert', 'frozen yogurt', 0.9),
    ('sweets', 'confectionery shop', 0.9), ('sweets', 'ice cream', 0.8),
    ('bakery', 'bakery shop', 0.95), ('bakery', 'pastry shop', 0.85),
    ('pizza', 'italian', 0.7), ('burgers', 'burger', 0.95), ('tacos', 'mexican', 0.85),
    ('vegetarian', 'vegan', 0.8),
    ('drinks', 'bar', 0.9), ('drinks', 'pub', 0.9), ('drinks', 'cafe', 0.6),
    ('nightlife', 'bar', 0.9), ('nightlife', 'pub', 0.9), ('nightlife', 'nightclub', 0.9),
    ('beer', 'pub', 0.9), ('beer', 'bar', 0.8), ('beer', 'brewery', 0.95),
    ('shopping', 'mall', 0.9), ('shopping', 'department store shop', 0.85),
    ('shopping', 'clothes shop', 0.8), ('shopping', 'gift shop', 0.8),
    ('shopping', 'variety store shop', 0.7), ('shopping', 'second hand shop', 0.75),
    ('thrift', 'second hand shop', 0.95), ('thrift', 'charity shop', 0.9),
    ('vintage', 'second hand shop', 0.85), ('vintage', 'antiques shop', 0.85),
    ('gifts', 'gift shop', 0.95), ('souvenirs', 'gift shop', 0.85),
    ('fitness', 'fitness centre', 0.95), ('fitness', 'sports centre', 0.85),
    ('gym', 'fitness centre', 0.95), ('sports', 'sports centre', 0.9),
    ('sports', 'sports shop', 0.8),
    ('outdoors', 'park', 0.9), ('outdoors', 'garden', 0.85), ('outdoors', 'nature reserve', 0.9),
    ('nature', 'park', 0.85), ('nature', 'garden', 0.85),
    ('games', 'video games shop', 0.85), ('games', 'games shop', 0.9),
    ('games', 'amusement arcade', 0.9), ('games', 'escape game', 0.85),
    ('movies', 'cinema', 0.95), ('film', 'cinema', 0.95),
    ('theater', 'theatre', 0.95), ('plants', 'garden centre shop', 0.9),
    ('plants', 'florist shop', 0.85), ('flowers', 'florist shop', 0.95),
    ('beauty', 'beauty shop', 0.9), ('beauty', 'cosmetics shop', 0.85),
    ('pets', 'pet shop', 0.95)
) s
ON t.interest = s.interest AND t.label = s.label
WHEN MATCHED THEN UPDATE SET weight = s.weight
WHEN NOT MATCHED THEN INSERT (interest, label, weight) VALUES (s.interest, s.label, s.weight);

-- Typical per-person spend by category, in US dollars. OSM has no prices, and the
-- API needs a cost per stop, so places get a labeled CATEGORY ESTIMATE (the highest
-- estimate among their tags), never presented as the place's own price. Categories
-- with no sensible visit spend (car repair, storage, phone shops, banks...) are left
-- out, so those places keep estimatedCost = null and the API won't use them as stops.
-- Rough planning figures for 2026, editable with MERGE (no redeploy needed).
CREATE TABLE IF NOT EXISTS CATEGORY_COST (
    label  STRING NOT NULL,
    usd    FLOAT NOT NULL
);

MERGE INTO CATEGORY_COST t
USING (
    SELECT column1 AS label, column2 AS usd FROM VALUES
    ('cafe', 6), ('coffee shop', 6), ('bubble tea', 7), ('juice', 7), ('ice cream', 6),
    ('frozen yogurt', 7), ('bakery shop', 6), ('deli shop', 10), ('cheese shop', 12),
    ('fast food', 11), ('burger', 12), ('sandwich', 11), ('chicken', 12), ('pizza', 14),
    ('mexican', 14), ('tex-mex', 14), ('chinese', 15), ('thai', 16), ('indian', 17),
    ('noodle', 15), ('asian', 15), ('american', 18), ('italian', 20), ('barbecue', 20),
    ('latin american', 15), ('breakfast', 15), ('restaurant', 20),
    ('bar', 15), ('pub', 18), ('nightclub', 20),
    ('library', 0), ('museum', 10), ('park', 0), ('community centre', 0), ('food sharing', 0),
    ('gift shop', 15), ('florist shop', 15), ('candles shop', 15), ('clothes shop', 25),
    ('video games shop', 20), ('amusement arcade', 15), ('fitness centre', 15),
    ('events venue', 25), ('garden centre shop', 15), ('supermarket shop', 8),
    ('convenience shop', 5), ('variety store shop', 8), ('department store shop', 20)
) s
ON t.label = s.label
WHEN MATCHED THEN UPDATE SET usd = s.usd
WHEN NOT MATCHED THEN INSERT (label, usd) VALUES (s.label, s.usd);

-- Cortex embeddings of category labels (filled by sql/04_load.sql).
CREATE TABLE IF NOT EXISTS CATEGORY_EMBEDDING (
    label        STRING NOT NULL,
    model        STRING NOT NULL,
    embedding    VECTOR(FLOAT, 768) NOT NULL,
    embedded_at  TIMESTAMP_TZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);

CREATE STAGE IF NOT EXISTS CODE COMMENT = 'lq_snowflake.zip for the UDF and procedure';
CREATE STAGE IF NOT EXISTS OSM COMMENT = 'OSM NDJSON uploads';
