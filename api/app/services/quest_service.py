import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from ..domain.locations import parse_locations
from ..domain.ports import LocationProvider, PreferenceExtractor, RoutePlanInput, RoutePlanner
from ..domain.preferences import normalize_preferences
from ..domain.route import RouteContext, prove_infeasible, validate_route
from ..domain.tasks import assign_tasks
from ..domain.types import CAMPUS_LOCATION, QUEST_TRAVEL_METHOD, Preferences, QuestRoute, UserRequest
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
        rng: random.Random | None = None,
    ) -> None:
        self._extractor = extractor
        self._locations = locations
        self._planner = planner
        self._timezone = timezone
        self._mock = mock  # when True, responses are labeled `mock: true`
        self._now = now
        self._rng = rng or random.Random()

    async def create_quest(self, request: UserRequest) -> QuestResult:
        # Quests always start and end at Cal Poly Pomona.
        address = CAMPUS_LOCATION.address

        # 1–4. The model extracts preferences; code applies defaults to anything missing/invalid.
        raw_preferences = await self._extractor.extract_preferences(request.message, address)
        # Quests are always driving quests, whatever travel method the message asked for.
        preferences = normalize_preferences(raw_preferences).model_copy(update={"travelMethod": QUEST_TRAVEL_METHOD})
        log.info("preferences normalized: %s", preferences.model_dump())

        # 5–6. Snowflake returns exactly 10 candidate locations.
        parsed = parse_locations(await self._locations.find_locations(preferences, address))
        if not parsed.ok:
            raise upstream_invalid("snowflake", "location list failed validation", parsed.issues)
        candidates = parsed.locations

        # 7–8. The model plans a round-trip route; code validates it against the candidates.
        start_time = local_clock(self._now(), self._timezone)
        # One random task per candidate; sent to the model and enforced on the returned stops.
        tasks = assign_tasks(candidates, self._rng)
        ctx = RouteContext(
            address=address,
            candidates=candidates,
            start_time=start_time,
            desired_time=preferences.desiredTime,
            desired_budget=preferences.desiredBudget,
            tasks=tasks,
        )
        # Proven impossible for every route: say so without spending a model call.
        if (proof := prove_infeasible(ctx)) is not None:
            raise AppError(
                422,
                "NO_FEASIBLE_ROUTE",
                proof.message,
                {"preferences": preferences.model_dump(), "reason": proof.reason, "proven": True},
            )

        issues: list[str] = []
        for attempt in range(1, MAX_PLAN_ATTEMPTS + 1):
            raw_route = await self._planner.plan_route(
                RoutePlanInput(
                    address=address,
                    preferences=preferences,
                    locations=candidates,
                    start_time=start_time,
                    timezone=self._timezone,
                    tasks=tasks,
                    facts=parsed.facts,
                    previous_issues=issues,
                )
            )
            result = validate_route(raw_route, ctx)
            if result.route is not None:
                if not result.route.quests:
                    # The planner's judgment, not a proof: label it so clients can word it accordingly.
                    raise AppError(
                        422,
                        "NO_FEASIBLE_ROUTE",
                        "The planner could not fit any stops into your time, budget, and opening hours. "
                        "Try allowing more time or budget, or a different preference.",
                        {"preferences": preferences.model_dump(), "reason": "PLANNER_FOUND_NONE", "proven": False},
                    )
                # 9. Return the validated route.
                route = result.route.model_copy(update={"mock": True}) if self._mock else result.route
                return QuestResult(route=route, preferences=preferences)
            issues = result.issues
            log.warning("route failed validation (attempt %d): %s", attempt, issues)

        raise upstream_invalid("cortex", "route failed validation", issues)
