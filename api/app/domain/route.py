"""Validate the planner's route. Code, not the model, owns: start/end address,
which places exist, no duplicates, time ordering, closing times, the time limit,
and the budget. The returned estimatedCost is summed from catalog costs; the
model's own cost total is ignored."""

import math
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .locations import clock_minutes, location_key, normalize_clock_time
from .types import LOCATION_COUNT, Location, Quest, QuestRoute, UserLocation

# A closing time earlier than this (e.g. "01:30") is read as "after midnight".
LATE_NIGHT_CUTOFF_MINUTES = 5 * 60
DAY = 24 * 60

_NonNeg = Field(ge=0, allow_inf_nan=False)


class _RawLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)


class _RawQuest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    location: _RawLocation
    arrivalTime: str = Field(min_length=1)
    departureTime: str = Field(min_length=1)
    travelDistance: float = _NonNeg


class _RawRoute(BaseModel):
    model_config = ConfigDict(extra="ignore")
    quests: list[_RawQuest] = Field(max_length=LOCATION_COUNT)
    totalTime: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    totalDistance: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    estimatedCost: float | None = Field(default=None, ge=0, allow_inf_nan=False)


@dataclass(frozen=True)
class RouteContext:
    address: str
    candidates: list[Location]
    start_time: str  # local "HH:MM"
    desired_time: int  # minutes available for the whole outing
    desired_budget: float  # US dollars


@dataclass(frozen=True)
class Infeasibility:
    reason: str
    message: str


def _closed_before_start(closing: int, start: int) -> bool:
    return closing <= start and closing >= LATE_NIGHT_CUTOFF_MINUTES


def prove_infeasible(ctx: RouteContext) -> Infeasibility | None:
    """Checks that hold for every possible route, so a failure is proof rather than a model's opinion."""
    start = clock_minutes(ctx.start_time) or 0
    open_now = [
        c for c in ctx.candidates if (m := clock_minutes(c.closingTime)) is None or not _closed_before_start(m, start)
    ]
    if not open_now:
        return Infeasibility("ALL_CLOSED", "Every candidate place is already closed. Try again earlier in the day.")
    if not any(c.estimatedCost is not None and c.estimatedCost <= ctx.desired_budget for c in open_now):
        return Infeasibility(
            "NONE_WITHIN_BUDGET",
            "No open candidate place has a known cost within your budget. Try a higher budget.",
        )
    return None


@dataclass(frozen=True)
class RouteValidationResult:
    route: QuestRoute | None
    issues: list[str]

    @property
    def ok(self) -> bool:
        return self.route is not None


def _r2(n: float) -> float:
    return round(n, 2)


def validate_route(raw: Any, ctx: RouteContext) -> RouteValidationResult:
    payload = raw
    if isinstance(payload, dict) and "route" in payload and "quests" not in payload:
        payload = payload["route"]

    try:
        parsed = _RawRoute.model_validate(payload, strict=False)
    except ValidationError as e:
        return RouteValidationResult(
            None, [f"{'.'.join(str(p) for p in err['loc']) or 'route'}: {err['msg']}" for err in e.errors()]
        )

    issues: list[str] = []
    by_key = {location_key(c.name, c.address): c for c in ctx.candidates}
    used: set[str] = set()
    start = clock_minutes(ctx.start_time) or 0

    def elapsed(minutes: int) -> int:
        # Minutes since quest start, wrapping past midnight.
        return (minutes - start) % DAY

    previous_departure = 0
    cost_total = 0.0
    quests: list[Quest] = []

    for i, q in enumerate(parsed.quests):
        at = f"quests[{i}]"
        key = location_key(q.location.name, q.location.address)
        candidate = by_key.get(key)
        if candidate is None:
            issues.append(f'{at}.location "{q.location.name}" is not one of the provided locations')
            continue
        if key in used:
            issues.append(f'{at}.location "{candidate.name}" appears more than once')
            continue
        used.add(key)

        arrival = clock_minutes(q.arrivalTime)
        departure = clock_minutes(q.departureTime)
        if arrival is None:
            issues.append(f'{at}.arrivalTime must be "HH:MM" 24-hour time')
        if departure is None:
            issues.append(f'{at}.departureTime must be "HH:MM" 24-hour time')

        if arrival is not None and departure is not None:
            a, d = elapsed(arrival), elapsed(departure)
            if a < previous_departure:
                issues.append(f"{at}.arrivalTime is before the previous departure")
            if d < a:
                issues.append(f"{at}.departureTime is before its arrivalTime")
            previous_departure = max(previous_departure, a, d)

            closing = clock_minutes(candidate.closingTime)
            if closing is not None:
                if _closed_before_start(closing, start) or d > elapsed(closing):
                    issues.append(f'{at} stays at "{candidate.name}" past its closing time {candidate.closingTime}')

        if candidate.estimatedCost is None:
            issues.append(f'{at}.location "{candidate.name}" has no known cost; choose places with an estimatedCost')
        else:
            cost_total += candidate.estimatedCost

        quests.append(
            Quest(
                location=candidate,
                arrivalTime=normalize_clock_time(q.arrivalTime),
                departureTime=normalize_clock_time(q.departureTime),
                travelDistance=_r2(q.travelDistance),
            )
        )

    # previous_departure is the last departure in minutes since start; the return trip only adds to it.
    if previous_departure > ctx.desired_time:
        issues.append(
            f"the last stop ends {previous_departure} minutes after the start, over the {ctx.desired_time}-minute limit"
        )
    if parsed.totalTime is not None:
        if parsed.totalTime > ctx.desired_time:
            issues.append(f"totalTime {parsed.totalTime:g} exceeds the {ctx.desired_time}-minute limit")
        elif parsed.totalTime < previous_departure:
            issues.append(f"totalTime {parsed.totalTime:g} is shorter than the {previous_departure} minutes the stops take")
    if _r2(cost_total) > ctx.desired_budget:
        issues.append(f"stops cost ${cost_total:.2f} in total, over the ${ctx.desired_budget:.2f} budget")

    if issues:
        return RouteValidationResult(None, issues)

    home = UserLocation(address=ctx.address)
    return RouteValidationResult(
        QuestRoute(
            # Start and end are always the user's own address, regardless of model output.
            startLocation=home,
            quests=quests,
            endLocation=home,
            totalTime=None if parsed.totalTime is None else int(math.floor(parsed.totalTime + 0.5)),
            totalDistance=None if parsed.totalDistance is None else _r2(parsed.totalDistance),
            estimatedCost=_r2(cost_total),
        ),
        [],
    )
