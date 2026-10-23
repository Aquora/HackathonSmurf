-- Hours parser UDF and the retrieval procedure, plus the backend grant. Re-run
-- after each upload of lq_snowflake.zip (scripts/lq.py deploy). Run as LQ_OWNER.

USE ROLE LQ_OWNER;
USE DATABASE IDENTIFIER($lq_db);
USE SCHEMA QUEST;

CREATE OR REPLACE FUNCTION PARSE_OSM_HOURS(opening_hours STRING)
    RETURNS ARRAY
    LANGUAGE PYTHON
    COMMENT = 'Weekly slots from OSM opening_hours; NULL when unsupported (= unknown)'
    RUNTIME_VERSION = '3.11'
    IMPORTS = ('@QUEST.CODE/lq_snowflake.zip')
    HANDLER = 'lq_snowflake.osm_hours.udf_parse';

CREATE OR REPLACE PROCEDURE GET_CANDIDATES(request VARIANT)
    RETURNS VARIANT
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.11'
    PACKAGES = ('snowflake-snowpark-python', 'tzdata')
    IMPORTS = ('@QUEST.CODE/lq_snowflake.zip')
    HANDLER = 'lq_snowflake.procedure.get_candidates'
    COMMENT = 'Top open Pomona places near the start that match the interests'
    EXECUTE AS OWNER;

GRANT USAGE ON DATABASE IDENTIFIER($lq_db) TO ROLE LQ_APP_RO;
GRANT USAGE ON SCHEMA QUEST TO ROLE LQ_APP_RO;
GRANT USAGE ON PROCEDURE GET_CANDIDATES(VARIANT) TO ROLE LQ_APP_RO;
