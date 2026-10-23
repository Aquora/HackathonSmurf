"""Parse the API's request into the values the search needs.

The API calls ``FIND_QUEST_LOCATIONS(request VARIANT, address STRING)`` with::

    {"desiredTime": 120, "desiredBudget": 25.0,
     "locationPreference": "coffee, art", "travelMethod": "walk"}

Errors raise ``LQ_INVALID_INPUT: <field>: <reason>``. The window starts now in
Pomona time. Unknown travel methods search with the walking radius. Budget is
validated and echoed but not used for filtering; costs are category estimates
(APP.CATEGORY_COST) that the API checks against the budget.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import settings
from .addresses import parse_address


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
    travel_method: str


def parse_request(payload, address, now, locate):
    """``locate(housenumber, street_core, postcode)`` returns ``(lat, lon, matched)`` or None."""
    if not isinstance(payload, dict):
        raise InvalidInput("request", "must be a JSON object")

    minutes = payload.get("desiredTime")
    if not _is_number(minutes) or not 0 < minutes <= settings.MAX_DESIRED_MINUTES:
        raise InvalidInput("desiredTime",
                           f"must be minutes between 1 and {settings.MAX_DESIRED_MINUTES}")
    available = int(round(minutes * 60))

    budget = payload.get("desiredBudget")
    if not _is_number(budget) or budget < 0:
        raise InvalidInput("desiredBudget", "must be a non-negative number of dollars")

    preference = payload.get("locationPreference", "")
    if preference is None:
        preference = ""
    if not isinstance(preference, str):
        raise InvalidInput("locationPreference", "must be a comma-separated string")
    interests = []
    for part in preference.split(","):
        value = part.strip().lower()
        if len(value) > settings.MAX_INTEREST_LENGTH:
            raise InvalidInput("locationPreference",
                               f"each preference must be at most {settings.MAX_INTEREST_LENGTH} characters")
        if value and value not in interests:
            interests.append(value)
    if len(interests) > settings.MAX_INTERESTS:
        raise InvalidInput("locationPreference", f"at most {settings.MAX_INTERESTS} preferences")

    travel = payload.get("travelMethod")
    if not isinstance(travel, str) or not travel.strip():
        raise InvalidInput("travelMethod", "must be a string such as walk, bike, transit, or drive")
    travel = travel.strip().lower()
    method = travel if travel in settings.TRAVEL else settings.DEFAULT_TRAVEL

    if not isinstance(address, str) or not address.strip() or len(address) > settings.MAX_ADDRESS_LENGTH:
        raise InvalidInput("address", "must be a street address")
    parsed = parse_address(address)
    if parsed is None:
        raise InvalidInput("address", "expected '<number> <street>, <city>, <state> <zip>'")
    located = locate(*parsed)
    if located is None:
        raise InvalidInput("address", "not found in the Pomona address data")
    latitude, longitude, matched = located

    window_start = now.replace(microsecond=0)
    return Request(
        request_id=f"lq_{uuid.uuid4().hex[:16]}",
        limit=settings.RESULT_LIMIT,
        constraints={
            "address": address,
            "matched_address": matched,
            "start": {"latitude": latitude, "longitude": longitude},
            "departure_time": window_start.isoformat(),
            "timezone": settings.TIMEZONE,
            "available_seconds": available,
            "budget": {"amount_minor": int(round(budget * 100)), "currency": settings.CURRENCY},
            "interests": interests,
            "travel_method": travel,
            "radius_travel_method": method,
        },
        latitude=latitude,
        longitude=longitude,
        window_start=window_start,
        window_end=window_start + timedelta(seconds=available),
        timezone=settings.TIMEZONE,
        available_seconds=available,
        interests=tuple(interests),
        travel_method=method,
    )


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
