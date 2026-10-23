"""Adapter interfaces. Adapters return raw, untrusted payloads; the quest service validates them."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from .types import Location, Preferences, QuestTask


@dataclass(frozen=True)
class RoutePlanInput:
    address: str
    preferences: Preferences
    locations: list[Location]
    start_time: str  # local "HH:MM"
    timezone: str
    # Randomly assigned task per location, keyed by location_key(name, address).
    tasks: dict[str, QuestTask] = field(default_factory=dict)
    previous_issues: list[str] = field(default_factory=list)  # for a single repair request


class PreferenceExtractor(Protocol):
    async def extract_preferences(self, message: str, address: str) -> Any: ...


class LocationProvider(Protocol):
    async def find_locations(self, preferences: Preferences, address: str) -> Any: ...


class RoutePlanner(Protocol):
    async def plan_route(self, request: RoutePlanInput) -> Any: ...
