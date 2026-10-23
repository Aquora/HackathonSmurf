"""Wire adapters from settings."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI

from .adapters.llm.chat_client import JsonChatClient
from .adapters.llm.cursor_adapter import CursorAdapter
from .adapters.mock.mock_adapters import MockLocationProvider, MockPreferenceExtractor, MockRoutePlanner
from .adapters.snowflake.cortex_client import CortexChatClient
from .adapters.snowflake.snowflake_adapter import SnowflakeLocationProvider, SnowflakePoolExecutor
from .config import Settings
from .domain.ports import LocationProvider, PreferenceExtractor, RoutePlanner
from .main import create_app
from .services.quest_service import QuestService


@dataclass
class Wiring:
    service: QuestService
    close: Callable[[], Awaitable[None]]


def build_service(settings: Settings) -> Wiring:
    closers: list[Callable[[], Awaitable[None]]] = []

    # One Snowflake pool, shared by the location lookup and the Cortex model step.
    executor: SnowflakePoolExecutor | None = None
    if settings.DATA_PROVIDER == "snowflake" or settings.AI_PROVIDER == "snowflake":
        executor = SnowflakePoolExecutor(settings)
        closers.append(executor.aclose)

    extractor: PreferenceExtractor
    planner: RoutePlanner
    if settings.AI_PROVIDER == "cursor":
        assert settings.CURSOR_API_KEY is not None and settings.CURSOR_MODEL is not None
        cursor = CursorAdapter(
            JsonChatClient(
                base_url=settings.cursor_base_url,
                api_key=settings.CURSOR_API_KEY.get_secret_value(),
                model=settings.CURSOR_MODEL,
                timeout_s=settings.CURSOR_TIMEOUT_S,
                max_retries=settings.CURSOR_MAX_RETRIES,
                json_mode=settings.CURSOR_JSON_MODE,
            )
        )
        extractor = planner = cursor
        closers.append(cursor.aclose)
    elif settings.AI_PROVIDER == "snowflake":
        assert executor is not None
        extractor = planner = CursorAdapter(
            CortexChatClient(executor, settings.SNOWFLAKE_AI_MODEL, settings.SNOWFLAKE_QUERY_TIMEOUT_S)
        )
    else:
        extractor, planner = MockPreferenceExtractor(), MockRoutePlanner()

    locations: LocationProvider
    if settings.DATA_PROVIDER == "snowflake":
        assert executor is not None
        locations = SnowflakeLocationProvider(
            executor, settings.SNOWFLAKE_LOCATIONS_PROCEDURE, settings.SNOWFLAKE_QUERY_TIMEOUT_S
        )
    else:
        locations = MockLocationProvider()

    async def close() -> None:
        for closer in closers:
            await closer()

    service = QuestService(
        extractor=extractor,
        locations=locations,
        planner=planner,
        timezone=settings.QUEST_TIMEZONE,
        mock=settings.uses_mock,
    )
    return Wiring(service=service, close=close)


def build_app(settings: Settings) -> FastAPI:
    wiring = build_service(settings)
    return create_app(
        wiring.service,
        cors_origins=settings.CORS_ORIGINS,
        rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        docs_enabled=settings.APP_ENV != "production",
        on_shutdown=wiring.close,
    )
