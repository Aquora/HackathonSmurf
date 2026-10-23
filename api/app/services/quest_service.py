import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from ..domain.locations import parse_locations
from ..domain.ports import LocationProvider, PreferenceExtractor, RoutePlanInput, RoutePlanner
from ..domain.preferences import normalize_preferences
from ..domain.route import RouteContext, validate_route
from ..domain.types import Preferences, QuestRoute, UserRequest
from ..errors import AppError, upstream_invalid

log = logging.getLogger(__name__)

# One repair attempt after an invalid route, then fail clearly.
MAX_PLAN_ATTEMPTS = 2


@dataclass(frozen=True)
class QuestResult:
    route: QuestRoute
    preferences: Preferences


def local_clock(now: datetime, timezone: str) -> str:
    """Wall-clock time as "HH:MM" in the given IANA time zone."""
    return now.astimezone(ZoneInfo(timezone)).strftime("%H:%M")


class QuestService:
    def __init__(
        self,
        *,
        extractor: PreferenceExtractor,
        locations: LocationProvider,
        planner: RoutePlanner,
        timezone: str,
        mock: bool,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._extractor = extractor
        self._locations = locations
        self._planner = planner
        self._timezone = timezone
        self._mock = mock  # when True, responses are labeled `mock: true`
        self._now = now

    async def create_quest(self, request: UserRequest) -> QuestResult:
        address = request.location.address

        # 1–4. Cursor extracts preferences; code applies defaults to anything missing/invalid.
        raw_preferences = await self._extractor.extract_preferences(request.message, address)
        preferences = normalize_preferences(raw_preferences)
        log.info("preferences normalized: %s", preferences.model_dump())

        # 5–6. Snowflake returns exactly 10 candidate locations.
        parsed = parse_locations(await self._locations.find_locations(preferences, address))
        if not parsed.ok:
            raise upstream_invalid("snowflake", "location list failed validation", parsed.issues)
        candidates = parsed.locations

        # 7–8. Cursor plans a round-trip route; code validates it against the candidates.
        start_time = local_clock(self._now(), self._timezone)
        issues: list[str] = []
        for attempt in range(1, MAX_PLAN_ATTEMPTS + 1):
            raw_route = await self._planner.plan_route(
                RoutePlanInput(
                    address=address,
                    preferences=preferences,
                    locations=candidates,
                    start_time=start_time,
                    timezone=self._timezone,
                    previous_issues=issues,
                )
            )
            result = validate_route(raw_route, RouteContext(address=address, candidates=candidates, start_time=start_time))
            if result.route is not None:
                if not result.route.quests:
                    raise AppError(
                        422,
                        "NO_FEASIBLE_ROUTE",
                        "No stops fit your time, budget, and opening hours right now. "
                        "Try allowing more time or budget, or a different preference.",
                        {"preferences": preferences.model_dump()},
                    )
                # 9. Return the validated route.
                route = result.route.model_copy(update={"mock": True}) if self._mock else result.route
                return QuestResult(route=route, preferences=preferences)
            issues = result.issues
            log.warning("route failed validation (attempt %d): %s", attempt, issues)

        raise upstream_invalid("cursor", "route failed validation", issues)
