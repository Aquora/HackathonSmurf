"""Validate the request JSON. Errors raise ``LQ_INVALID_INPUT: <field>: <reason>``.

The backend applies defaults before calling Snowflake; anything malformed is
rejected here instead of being filled in. Budget is validated for contract
compatibility but not used for filtering: OpenStreetMap has no prices.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import settings


class InvalidInput(ValueError):
    def __init__(self, field, reason):
        super().__init__(f"LQ_INVALID_INPUT: {field}: {reason}")
        self.field = field


@dataclass(frozen=True)
class Request:
    request_id: str
    limit: int
    constraints: dict
    latitude: float
    longitude: float
    window_start: datetime
    window_end: datetime
    timezone: str
    available_seconds: int
    interests: tuple


def validate_request(payload):
    if not isinstance(payload, dict):
        raise InvalidInput("request", "must be a JSON object")

    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
        raise InvalidInput("request_id", "must be a non-empty string up to 128 characters")

    limit = payload.get("limit")
    if not _is_int(limit) or not 1 <= limit <= settings.LIMIT_CAP:
        raise InvalidInput("limit", f"must be an integer from 1 to {settings.LIMIT_CAP}")

    constraints = payload.get("constraints")
    if not isinstance(constraints, dict):
        raise InvalidInput("constraints", "must be an object")

    start = constraints.get("start")
    if not isinstance(start, dict):
        raise InvalidInput("constraints.start", "must be an object")
    latitude = start.get("latitude")
    longitude = start.get("longitude")
    if not _is_number(latitude) or not -90 <= latitude <= 90:
        raise InvalidInput("constraints.start.latitude", "must be between -90 and 90")
    if not _is_number(longitude) or not -180 <= longitude <= 180:
        raise InvalidInput("constraints.start.longitude", "must be between -180 and 180")

    tz_name = constraints.get("timezone")
    if not isinstance(tz_name, str):
        raise InvalidInput("constraints.timezone", "must be an IANA timezone name")
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise InvalidInput("constraints.timezone", "unknown IANA timezone") from None

    departure = constraints.get("departure_time")
    try:
        window_start = datetime.fromisoformat(departure) if isinstance(departure, str) else None
    except ValueError:
        window_start = None
    if window_start is None or window_start.tzinfo is None:
        raise InvalidInput("constraints.departure_time", "must be ISO 8601 with an offset")

    available = constraints.get("available_seconds")
    if not _is_int(available) or available <= 0 or available > 86400:
        raise InvalidInput("constraints.available_seconds", "must be an integer from 1 to 86400")

    budget = constraints.get("budget")
    if not isinstance(budget, dict):
        raise InvalidInput("constraints.budget", "must be a money object")
    amount = budget.get("amount_minor")
    if not _is_int(amount) or amount < 0:
        raise InvalidInput("constraints.budget.amount_minor", "must be a non-negative integer")
    if budget.get("currency") not in settings.SUPPORTED_CURRENCIES:
        raise InvalidInput("constraints.budget.currency", "unsupported currency")

    interests = constraints.get("interests")
    if not isinstance(interests, list):
        raise InvalidInput("constraints.interests", "must be an array")
    if len(interests) > settings.MAX_INTERESTS:
        raise InvalidInput("constraints.interests", f"at most {settings.MAX_INTERESTS} entries")
    cleaned = []
    for item in interests:
        value = item.strip().lower() if isinstance(item, str) else ""
        if not value or len(value) > settings.MAX_INTEREST_LENGTH:
            raise InvalidInput("constraints.interests", "entries must be 1-64 character strings")
        if value not in cleaned:
            cleaned.append(value)

    return Request(
        request_id=request_id,
        limit=limit,
        constraints=constraints,
        latitude=float(latitude),
        longitude=float(longitude),
        window_start=window_start,
        window_end=window_start + timedelta(seconds=available),
        timezone=tz_name,
        available_seconds=available,
        interests=tuple(cleaned),
    )


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
