"""Local Quest Snowflake candidate retrieval.

Pure modules (osm_hours, hours, request, ranking) have no Snowflake dependency
and are unit-tested locally. procedure.py is the stored-procedure handler that
runs the SQL inside Snowflake and delegates filtering/ranking to the pure modules.
"""
