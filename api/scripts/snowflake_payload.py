"""Print exactly what the API would send to Snowflake, without calling Snowflake.

Usage (from api/):
    .venv/bin/python -m scripts.snowflake_payload "2 hours, $25, coffee, walking" "123 Main St, Pomona, CA"
    .venv/bin/python -m scripts.snowflake_payload --cursor "..." "..."   # use the real Cursor model from .env

Prints the SQL statement and its two bound parameters.
"""

import argparse
import asyncio
import json
from unittest.mock import AsyncMock

from app.adapters.mock.mock_adapters import MockPreferenceExtractor
from app.adapters.snowflake.snowflake_adapter import SnowflakeLocationProvider
from app.config import load_settings
from app.domain.preferences import normalize_preferences


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("message")
    parser.add_argument("address")
    parser.add_argument("--cursor", action="store_true", help="extract preferences with the configured Cursor model")
    args = parser.parse_args()

    settings = load_settings(**({"AI_PROVIDER": "cursor"} if args.cursor else {}))
    if args.cursor:
        from app.container import build_service

        extractor = build_service(settings).service._extractor
    else:
        extractor = MockPreferenceExtractor()

    raw = await extractor.extract_preferences(args.message, args.address)
    preferences = normalize_preferences(raw)

    # Fake executor: records the call instead of running it.
    executor = AsyncMock()
    executor.execute.return_value = [{"RESULT": "[]"}]
    provider = SnowflakeLocationProvider(executor, settings.SNOWFLAKE_LOCATIONS_PROCEDURE, settings.SNOWFLAKE_QUERY_TIMEOUT_S)
    await provider.find_locations(preferences, args.address)
    sql, params, _ = executor.execute.await_args.args

    print("Extractor:", "Cursor" if args.cursor else "mock (regex)")
    print("Raw extractor output:", json.dumps(raw))
    print("\nSQL:", sql)
    print("Param 1 (preferences JSON):")
    print(json.dumps(json.loads(params[0]), indent=2))
    print("Param 2 (address):", params[1])
    print("\nPaste into a Snowflake worksheet to test the procedure directly:")
    def quote(text: str) -> str:
        return "'" + text.replace("\\", "\\\\").replace("'", "''") + "'"

    print(f"CALL {settings.SNOWFLAKE_LOCATIONS_PROCEDURE}(PARSE_JSON({quote(params[0])}), {quote(params[1])});")


if __name__ == "__main__":
    asyncio.run(main())
