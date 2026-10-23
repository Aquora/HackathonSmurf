-- Replace the dataset with the staged OSM NDJSON, parse hours, and embed any new
-- category labels. scripts/lq.py load fetches the data, uploads it to @QUEST.OSM,
-- and sets $lq_db and $embed_model before running this file. Run as LQ_OWNER.

USE ROLE LQ_OWNER;
USE DATABASE IDENTIFIER($lq_db);
USE SCHEMA QUEST;

CREATE OR REPLACE TEMPORARY TABLE OSM_STAGE (raw VARIANT);
COPY INTO OSM_STAGE (raw) FROM @OSM FILE_FORMAT = (TYPE = JSON) FORCE = TRUE;

BEGIN TRANSACTION;

DELETE FROM PLACE;
INSERT INTO PLACE (place_id, osm_ref, name, tags, latitude, longitude, point,
                   address, website, opening_hours_raw, snapshot_date)
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
       raw:snapshot_date::DATE
FROM OSM_STAGE
WHERE raw:name IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw:osm_ref::STRING ORDER BY raw:osm_ref::STRING) = 1;

DELETE FROM PLACE_HOURS;
INSERT INTO PLACE_HOURS (place_id, day_of_week, open_minute, close_minute)
SELECT p.place_id, s.value:day_of_week::NUMBER, s.value:open_minute::NUMBER,
       s.value:close_minute::NUMBER
FROM PLACE p, LATERAL FLATTEN(input => PARSE_OSM_HOURS(p.opening_hours_raw)) s;

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
       (SELECT COUNT(*) FROM CATEGORY_EMBEDDING WHERE model = $embed_model) AS embedded_labels;
