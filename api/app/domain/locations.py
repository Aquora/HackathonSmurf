import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .types import LOCATION_COUNT, Location

_HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d(?:\.\d+)?)?$")


def normalize_clock_time(value: str) -> str:
    """Normalize "9:05" or "09:05:00" to "09:05"; leave other strings untouched (trimmed)."""
    m = _HHMM.match(value.strip())
    if not m:
        return value.strip()
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def clock_minutes(value: str) -> int | None:
    """Minutes after midnight for "HH:MM", or None if not a clock time."""
    m = _HHMM.match(value.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def location_key(name: str, address: str) -> str:
    return f"{name.strip().lower()}|{' '.join(address.strip().lower().split())}"


def _pick(row: Mapping[str, Any], *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is not None:
            return value
    return None


_INVALID = object()


def _to_cost(value: Any) -> Any:
    """Catalog cost in dollars: None if absent (unknown), _INVALID if unusable."""
    if value is None:
        return None
    if isinstance(value, bool):
        return _INVALID
    try:
        cost = float(value)  # numbers, Decimal from the connector, numeric strings
    except (TypeError, ValueError):
        return _INVALID
    return round(cost, 2) if math.isfinite(cost) and cost >= 0 else _INVALID


@dataclass(frozen=True)
class CandidateFacts:
    """What Snowflake knows about a candidate beyond the wire Location. Prompt-only: these are
    OpenStreetMap-derived strings (untrusted data), shown to the planner so it judges places by
    category instead of by name. Never returned to clients."""

    categories: list[str]
    # Why the place matched the user's preferences, e.g. "tag 'cafe' related to interest 'coffee'".
    # Empty = it was added only to reach 10 candidates.
    preference_matches: list[str]
    # The same matches, structured: (interest, "exact" | "related" | "weak").
    interest_matches: list[tuple[str, str]]
    rank: int | None
    distance_miles: float | None
    within_range: bool | None


_MAX_FACTS = 6
_MAX_FACT_LENGTH = 80
# Snowflake's wording (snowflake/python/lq_snowflake/ranking.py match_reasons) -> match strength.
_MATCH_PATTERNS = (
    (re.compile(r"^tag '.*' matches interest '(.+)'$"), "exact"),
    (re.compile(r"^tag '.*' related to interest '(.+)'$"), "related"),
    (re.compile(r"^tag '.*' is the closest category to '(.+)'"), "weak"),
)


def _interest_matches(reasons: list[str]) -> list[tuple[str, str]]:
    matches = []
    for reason in reasons:
        for pattern, strength in _MATCH_PATTERNS:
            if m := pattern.match(reason):
                matches.append((m.group(1), strength))
                break
    return matches


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out = [" ".join(v.split())[:_MAX_FACT_LENGTH] for v in value if isinstance(v, str) and v.strip()]
    return out[:_MAX_FACTS]


def _facts(row: Mapping[str, Any]) -> CandidateFacts:
    reasons = _strings(_pick(row, "match_reasons", "matchReasons"))
    rank = _pick(row, "rank")
    distance = _pick(row, "distance_m", "distanceM")
    within = _pick(row, "within_radius", "withinRadius")
    try:
        miles = round(float(distance) / 1609.344, 1) if distance is not None and float(distance) >= 0 else None
    except (TypeError, ValueError):
        miles = None
    return CandidateFacts(
        categories=_strings(_pick(row, "tags")),
        # Snowflake phrases preference matches as "tag '<label>' ..."; the rest are distance notes.
        preference_matches=[r for r in reasons if r.startswith("tag '")],
        interest_matches=_interest_matches(reasons),
        rank=rank if isinstance(rank, int) and not isinstance(rank, bool) and rank > 0 else None,
        distance_miles=miles,
        within_range=within if isinstance(within, bool) else None,
    )


@dataclass(frozen=True)
class LocationParseResult:
    locations: list[Location]
    issues: list[str]
    # Keyed by location_key(name, address).
    facts: dict[str, CandidateFacts] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.issues


def parse_locations(raw: Any) -> LocationParseResult:
    """Validate the Snowflake payload.

    Accepts a list of rows or {"locations": [...]}, tolerates Snowflake's upper-cased
    keys and TIME values, and requires exactly LOCATION_COUNT unique locations.
    """
    payload = raw
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return LocationParseResult([], ["payload is not valid JSON"])
    if isinstance(payload, dict):
        payload = _pick(payload, "locations")
    if not isinstance(payload, list):
        return LocationParseResult([], ["expected an array of locations"])

    issues: list[str] = []
    locations: list[Location] = []
    seen: set[str] = set()
    facts: dict[str, CandidateFacts] = {}

    for i, row in enumerate(payload):
        if not isinstance(row, dict):
            issues.append(f"locations[{i}] is not an object")
            continue
        name = _pick(row, "name")
        address = _pick(row, "address")
        closing = _pick(row, "closingTime", "closing_time")
        if hasattr(closing, "strftime"):  # datetime.time from the connector
            closing = closing.strftime("%H:%M")
        missing = False
        for field, value in (("name", name), ("address", address), ("closingTime", closing)):
            if not isinstance(value, str) or not value.strip():
                issues.append(f"locations[{i}].{field} is missing")
                missing = True
        if missing:
            continue

        cost = _to_cost(_pick(row, "estimatedCost", "estimated_cost"))
        if cost is _INVALID:
            issues.append(f"locations[{i}].estimatedCost must be a non-negative number")
            continue

        key = location_key(name, address)
        if key in seen:
            issues.append(f"locations[{i}] duplicates an earlier location")
            continue
        seen.add(key)
        facts[key] = _facts(row)
        locations.append(
            Location(name=name.strip(), address=address.strip(), closingTime=normalize_clock_time(closing), estimatedCost=cost)
        )

    if not issues and len(locations) != LOCATION_COUNT:
        issues.append(f"expected exactly {LOCATION_COUNT} locations, received {len(locations)}")
    return LocationParseResult([] if issues else locations, issues, {} if issues else facts)
