"""Shared domain models. Wire format is camelCase JSON.

Units: time in minutes, money in US dollars, distance in miles, clock times "HH:MM" local.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

KNOWN_TRAVEL_METHODS = ("drive", "walk", "bike", "transit")
# Known methods are "drive" | "walk" | "bike" | "transit"; any other non-empty string is passed through.
TravelMethod = str

LOCATION_COUNT = 10
MESSAGE_MAX_LENGTH = 2000
ADDRESS_MAX_LENGTH = 300


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class UserLocation(_Model):
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=ADDRESS_MAX_LENGTH)]


class UserRequest(_Model):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_LENGTH)]
    location: UserLocation


class Preferences(_Model):
    desiredTime: int
    desiredBudget: float
    locationPreference: str
    travelMethod: TravelMethod


DEFAULT_PREFERENCES = Preferences(desiredTime=90, desiredBudget=30, locationPreference="random", travelMethod="drive")


class Location(_Model):
    name: str
    address: str
    closingTime: str
    # Typical spend in US dollars from the catalog; None = unknown (cannot prove the budget).
    estimatedCost: float | None = None


class Quest(_Model):
    location: Location
    arrivalTime: str
    departureTime: str
    travelDistance: float


class QuestRoute(_Model):
    startLocation: UserLocation
    quests: list[Quest]
    endLocation: UserLocation
    totalTime: int | None = None
    totalDistance: float | None = None
    estimatedCost: float | None = None
    # Present and true only when mock adapters produced this response.
    mock: Literal[True] | None = None
