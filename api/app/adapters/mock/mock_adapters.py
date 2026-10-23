"""Deterministic offline adapters for local development, tests, and labeled demos.

The locations are fictional; responses produced with these adapters carry `mock: true`.
"""

import re
from typing import Any

from ...domain.locations import clock_minutes, location_key
from ...domain.ports import RoutePlanInput
from ...domain.types import Location

MOCK_LOCATIONS: list[Location] = [
    Location(name="Demo Bean Coffee", address="101 Example Ave, Demo City, CA 90000", closingTime="18:00", estimatedCost=6),
    Location(name="Demo Gallery of Art", address="202 Sample St, Demo City, CA 90000", closingTime="17:00", estimatedCost=0),
    Location(name="Demo Botanical Garden", address="303 Placeholder Rd, Demo City, CA 90000", closingTime="19:00", estimatedCost=10),
    Location(name="Demo Used Bookshop", address="404 Fixture Ln, Demo City, CA 90000", closingTime="20:00", estimatedCost=15),
    Location(name="Demo Taco Stand", address="505 Mock Blvd, Demo City, CA 90000", closingTime="22:00", estimatedCost=12),
    Location(name="Demo History Museum", address="606 Test Way, Demo City, CA 90000", closingTime="16:30", estimatedCost=18),
    Location(name="Demo Record Store", address="707 Stub Ct, Demo City, CA 90000", closingTime="21:00", estimatedCost=20),
    Location(name="Demo Lookout Park", address="808 Dummy Dr, Demo City, CA 90000", closingTime="23:00", estimatedCost=0),
    Location(name="Demo Ice Cream Parlor", address="909 Sample St, Demo City, CA 90000", closingTime="22:30", estimatedCost=7),
    Location(name="Demo Arcade", address="1010 Example Ave, Demo City, CA 90000", closingTime="23:59", estimatedCost=25),
]

_KEYWORDS = ["coffee", "art", "garden", "park", "book", "food", "taco", "museum", "history", "music", "record", "ice cream", "arcade", "game"]  # fmt: skip
_HOURS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b")
_MINUTES = re.compile(r"(\d+)\s*(?:minutes?|mins?)\b")
_DOLLARS = re.compile(r"\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:dollars|bucks)")
_TRAVEL = re.compile(r"\b(walk(?:ing)?|on foot|bike|biking|cycling|transit|bus|train|drive|driving|car)\b")


class MockPreferenceExtractor:
    async def extract_preferences(self, message: str, address: str) -> Any:
        text = message.lower()
        hours, minutes, dollars, travel = _HOURS.search(text), _MINUTES.search(text), _DOLLARS.search(text), _TRAVEL.search(text)
        interests = [k for k in _KEYWORDS if k in text]
        return {
            "desiredTime": float(hours.group(1)) * 60 if hours else int(minutes.group(1)) if minutes else None,
            "desiredBudget": float(dollars.group(1) or dollars.group(2)) if dollars else None,
            "locationPreference": ", ".join(interests) if interests else None,
            "travelMethod": travel.group(1) if travel else None,
        }


class MockLocationProvider:
    async def find_locations(self, preferences: Any, address: str) -> Any:
        return [loc.model_dump() for loc in MOCK_LOCATIONS]


_SPEED_MPH = {"walk": 3, "bike": 10, "transit": 12, "drive": 25}
_VISIT_MINUTES = 20
_LEG_MILES = 1


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


class MockRoutePlanner:
    """Greedy planner: visits locations still open and affordable, while time and a three-stop cap allow."""

    async def plan_route(self, request: RoutePlanInput) -> Any:
        speed = _SPEED_MPH.get(request.preferences.travelMethod, _SPEED_MPH["drive"])
        leg = max(1, round(_LEG_MILES / speed * 60))
        start = clock_minutes(request.start_time)
        start = 9 * 60 if start is None else start
        now = start
        spent = 0.0
        quests: list[dict[str, Any]] = []

        for loc in request.locations:
            if len(quests) >= 3:
                break
            arrival = now + leg
            departure = arrival + _VISIT_MINUTES
            if departure >= 24 * 60:
                break
            closing = clock_minutes(loc.closingTime)
            if closing is not None and departure > closing:
                continue
            if loc.estimatedCost is None or spent + loc.estimatedCost > request.preferences.desiredBudget:
                continue
            if departure + leg - start > request.preferences.desiredTime:
                break
            task = request.tasks.get(location_key(loc.name, loc.address))
            quests.append(
                {
                    "location": loc.model_dump(),
                    "arrivalTime": _hhmm(arrival),
                    "departureTime": _hhmm(departure),
                    "travelDistance": _LEG_MILES,
                    "task": task.model_dump() if task else None,
                    "description": f"[Demo] Stop {len(quests) + 1}: visit {loc.name} on your way around the quest.",
                }
            )
            now = departure
            spent += loc.estimatedCost

        return {
            "startLocation": {"address": request.address},
            "quests": quests,
            "endLocation": {"address": request.address},
            "totalTime": now + leg - start,
            "totalDistance": (len(quests) + 1) * _LEG_MILES,
            "estimatedCost": spent,
        }
