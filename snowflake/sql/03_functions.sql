-- Hours parser UDF and the retrieval procedure, plus the backend grant. Re-run
-- after each upload of lq_snowflake.zip (scripts/lq.py deploy). Run as LQ_OWNER.

USE ROLE LQ_OWNER;
USE DATABASE IDENTIFIER($lq_db);
USE SCHEMA APP;

CREATE OR REPLACE FUNCTION PARSE_OSM_HOURS(opening_hours STRING)
    RETURNS ARRAY
    LANGUAGE PYTHON
    COMMENT = 'Weekly slots from OSM opening_hours; NULL when unsupported (= unknown)'
    RUNTIME_VERSION = '3.11'
    IMPORTS = ('@APP.CODE/lq_snowflake.zip')
    HANDLER = 'lq_snowflake.osm_hours.udf_parse';

CREATE OR REPLACE PROCEDURE FIND_QUEST_LOCATIONS(request VARIANT, address STRING)
    RETURNS VARIANT
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'tzdata')
    IMPORTS = ('@APP.CODE/lq_snowflake.zip')
    HANDLER = 'lq_snowflake.procedure.find_quest_locations'
    COMMENT = 'Top 10 open Pomona places near the address that match the preferences'
    EXECUTE AS OWNER;

GRANT USAGE ON DATABASE IDENTIFIER($lq_db) TO ROLE LQ_APP_RO;
GRANT USAGE ON SCHEMA APP TO ROLE LQ_APP_RO;
GRANT USAGE ON PROCEDURE FIND_QUEST_LOCATIONS(VARIANT, STRING) TO ROLE LQ_APP_RO;
