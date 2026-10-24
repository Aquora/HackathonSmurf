-- Replace places and addresses with the staged OSM NDJSON, parse hours, and embed
-- any new category labels. scripts/lq.py load fetches both files, uploads them to
-- @APP.OSM, and sets $lq_db and $embed_model before running this file. Run as LQ_OWNER.

USE ROLE LQ_OWNER;
USE DATABASE IDENTIFIER($lq_db);
USE SCHEMA APP;

CREATE OR REPLACE TEMPORARY TABLE OSM_STAGE (raw VARIANT);
COPY INTO OSM_STAGE (raw) FROM @OSM PATTERN = '.*osm_pomona_places[.]ndjson.*'
    FILE_FORMAT = (TYPE = JSON) FORCE = TRUE;
CREATE OR REPLACE TEMPORARY TABLE ADDRESS_STAGE (raw VARIANT);
COPY INTO ADDRESS_STAGE (raw) FROM @OSM PATTERN = '.*osm_pomona_addresses[.]ndjson.*'
    FILE_FORMAT = (TYPE = JSON) FORCE = TRUE;

BEGIN TRANSACTION;

DELETE FROM PLACE;
INSERT INTO PLACE (place_id, osm_ref, name, tags, latitude, longitude, point,
                   address, website, opening_hours_raw, snapshot_date, brand, brand_wikidata)
SELECT 'osm_' || REPLACE(raw:osm_ref::STRING, '/', '_'),
       raw:osm_ref::STRING,
       raw:name::STRING,
       raw:categories::ARRAY,
       raw:latitude::FLOAT,
       raw:longitude::FLOAT,
       ST_MAKEPOINT(raw:longitude::FLOAT, raw:latitude::FLOAT),
       raw:address::STRING,
       raw:website::STRING,
       raw:opening_hours::STRING,
       raw:snapshot_date::DATE,
       NULLIF(TRIM(raw:brand::STRING), ''),
       NULLIF(TRIM(raw:brand_wikidata::STRING), '')
FROM OSM_STAGE
WHERE raw:name IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw:osm_ref::STRING ORDER BY raw:osm_ref::STRING) = 1;

-- Flag chains (data only; nothing is filtered here). In order of strength:
--   brand_tag      the place has an OSM brand or brand:wikidata tag
--   brand_name     its name matches another place's brand (an untagged chain location)
--   repeated_name  the same name appears at more than one place in the dataset
-- Names are compared lowercase with punctuation and spaces removed ("McDonald's" = "mcdonalds").
UPDATE PLACE p
SET is_chain = (f.reason IS NOT NULL), chain_reason = f.reason
FROM (
    SELECT n.place_id,
           CASE
               WHEN n.brand IS NOT NULL OR n.brand_wikidata IS NOT NULL THEN 'brand_tag'
               WHEN b.brand_key IS NOT NULL THEN 'brand_name'
               WHEN n.name_key <> '' AND COUNT(*) OVER (PARTITION BY n.name_key) > 1 THEN 'repeated_name'
           END AS reason
    FROM (SELECT place_id, brand, brand_wikidata,
                 REGEXP_REPLACE(LOWER(name), '[^a-z0-9]', '') AS name_key
          FROM PLACE) n
    LEFT JOIN (SELECT DISTINCT REGEXP_REPLACE(LOWER(brand), '[^a-z0-9]', '') AS brand_key
               FROM PLACE WHERE brand IS NOT NULL) b
           ON b.brand_key = n.name_key AND b.brand_key <> ''
) f
WHERE p.place_id = f.place_id;

DELETE FROM PLACE_HOURS;
INSERT INTO PLACE_HOURS (place_id, day_of_week, open_minute, close_minute)
SELECT p.place_id, s.value:day_of_week::NUMBER, s.value:open_minute::NUMBER,
       s.value:close_minute::NUMBER
FROM PLACE p, LATERAL FLATTEN(input => PARSE_OSM_HOURS(p.opening_hours_raw)) s;

DELETE FROM ADDRESS;
INSERT INTO ADDRESS (osm_ref, housenumber, street, street_core, postcode, latitude, longitude,
                     snapshot_date)
SELECT raw:osm_ref::STRING, raw:housenumber::STRING, raw:street::STRING,
       raw:street_core::STRING, raw:postcode::STRING, raw:latitude::FLOAT,
       raw:longitude::FLOAT, raw:snapshot_date::DATE
FROM ADDRESS_STAGE;

COMMIT;

-- Embed category labels not yet embedded (Cortex calls cost credits).
INSERT INTO CATEGORY_EMBEDDING (label, model, embedding)
SELECT l.label, $embed_model, AI_EMBED($embed_model, l.label)
FROM (SELECT DISTINCT t.value::STRING AS label
      FROM PLACE, LATERAL FLATTEN(input => tags) t) l
WHERE NOT EXISTS (SELECT 1 FROM CATEGORY_EMBEDDING e
                  WHERE e.label = l.label AND e.model = $embed_model);

SELECT (SELECT COUNT(*) FROM PLACE) AS places,
       (SELECT COUNT(DISTINCT place_id) FROM PLACE_HOURS) AS places_with_hours,
       (SELECT COUNT(*) FROM PLACE WHERE is_chain) AS chain_places,
       (SELECT COUNT(*) FROM ADDRESS) AS addresses,
       (SELECT COUNT(*) FROM CATEGORY_EMBEDDING WHERE model = $embed_model) AS embedded_labels;
