import json
import re
from dataclasses import dataclass
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


@dataclass(frozen=True)
class LocationParseResult:
    locations: list[Location]
    issues: list[str]

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

        key = location_key(name, address)
        if key in seen:
            issues.append(f"locations[{i}] duplicates an earlier location")
            continue
        seen.add(key)
        locations.append(Location(name=name.strip(), address=address.strip(), closingTime=normalize_clock_time(closing)))

    if not issues and len(locations) != LOCATION_COUNT:
        issues.append(f"expected exactly {LOCATION_COUNT} locations, received {len(locations)}")
    return LocationParseResult([] if issues else locations, issues)
