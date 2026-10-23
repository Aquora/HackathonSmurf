-- Local Quest: candidate location lookup used by the API (api/app/adapters/snowflake).
-- Status: reference implementation, NOT yet run against a Snowflake account.
--
-- Contract with the API:
--   CALL <db>.<schema>.FIND_QUEST_LOCATIONS(PARSE_JSON(:preferences_json), :address)
--   address is always Cal Poly Pomona: '3801 W Temple Ave, Pomona, CA 91768'.
--   preferences: { desiredTime, desiredBudget, locationPreference, travelMethod }
--   returns VARIANT: array of exactly 10 objects
--     { "name", "address", "closingTime" ("HH:MM", 24h local), "estimatedCost" (USD, omitted when unknown) }
-- The API rejects any result that is not exactly 10 unique locations.
--
-- Limitations: there is no geocoding here. Locality is approximated by matching the
-- place's city against the start address text (so places in Pomona rank first). Replace with geospatial ranking
-- (e.g. ST_DISTANCE on a GEOGRAPHY column) once start coordinates are available.

CREATE DATABASE IF NOT EXISTS LOCAL_QUEST;
CREATE SCHEMA IF NOT EXISTS LOCAL_QUEST.APP;

CREATE TABLE IF NOT EXISTS LOCAL_QUEST.APP.PLACES (
  PLACE_ID        STRING        NOT NULL PRIMARY KEY,
  NAME            STRING        NOT NULL,
  ADDRESS         STRING        NOT NULL,
  CITY            STRING        NOT NULL,
  CATEGORY        STRING        NOT NULL,   -- e.g. 'coffee', 'art', 'park'
  CLOSING_TIME    TIME          NOT NULL,   -- local closing time
  ESTIMATED_COST  NUMBER(8, 2),             -- typical spend in USD; NULL = unknown
  SOURCE_URL      STRING,
  VERIFIED_AT     TIMESTAMP_TZ,
  IS_DEMO         BOOLEAN       DEFAULT FALSE
);

CREATE OR REPLACE PROCEDURE LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS(PREFS VARIANT, START_ADDRESS STRING)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  pref   STRING DEFAULT LOWER(COALESCE(PREFS:locationPreference::STRING, 'random'));
  budget FLOAT  DEFAULT COALESCE(PREFS:desiredBudget::FLOAT, 30);
  addr   STRING DEFAULT LOWER(COALESCE(START_ADDRESS, ''));
  result VARIANT;
BEGIN
  SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
           'name', NAME,
           'address', ADDRESS,
           'closingTime', TO_VARCHAR(CLOSING_TIME, 'HH24:MI'),
           'estimatedCost', ESTIMATED_COST))  -- OBJECT_CONSTRUCT drops the key when NULL (unknown)
         WITHIN GROUP (ORDER BY SCORE DESC, TIEBREAK)
    INTO :result
    FROM (
      SELECT NAME, ADDRESS, CLOSING_TIME, ESTIMATED_COST,
             IFF(CONTAINS(:addr, LOWER(CITY)), 2, 0)
               + IFF(:pref <> 'random' AND CONTAINS(:pref, LOWER(CATEGORY)), 3, 0)
               + IFF(ESTIMATED_COST IS NOT NULL AND ESTIMATED_COST <= :budget, 1, 0) AS SCORE,
             RANDOM() AS TIEBREAK
        FROM LOCAL_QUEST.APP.PLACES
       ORDER BY SCORE DESC, TIEBREAK
       LIMIT 10
    );
  RETURN COALESCE(result, ARRAY_CONSTRUCT());
END;
$$;

-- Least-privilege role for the API service user (adjust names to your account):
-- CREATE ROLE IF NOT EXISTS LOCAL_QUEST_API;
-- GRANT USAGE ON WAREHOUSE <warehouse> TO ROLE LOCAL_QUEST_API;
-- GRANT USAGE ON DATABASE LOCAL_QUEST TO ROLE LOCAL_QUEST_API;
-- GRANT USAGE ON SCHEMA LOCAL_QUEST.APP TO ROLE LOCAL_QUEST_API;
-- GRANT USAGE ON PROCEDURE LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS(VARIANT, STRING) TO ROLE LOCAL_QUEST_API;
