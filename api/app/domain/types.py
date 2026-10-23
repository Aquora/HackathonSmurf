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
# Start address used when a request omits `location` (Cal Poly Pomona; in Snowflake's Pomona address data).


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class UserLocation(_Model):
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=ADDRESS_MAX_LENGTH)]


# Every quest starts and ends at Cal Poly Pomona; users cannot choose a different start.
CAMPUS_LOCATION = UserLocation(address="3801 W Temple Ave, Pomona, CA 91768")


class UserRequest(_Model):
    # Unknown fields (e.g. a legacy `location`) are ignored; the start is always CAMPUS_LOCATION.
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_LENGTH)]


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


TaskId = Literal["photo_inside", "photo_building", "review_screenshot"]


class QuestTask(_Model):
    id: TaskId
    text: str


# Each stop gets exactly one of these, chosen at random by code (see domain/tasks.py).
QUEST_TASKS: tuple[QuestTask, ...] = (
    QuestTask(id="photo_inside", text="Take a picture of the inside"),
    QuestTask(id="photo_building", text="Take a picture of the building"),
    QuestTask(id="review_screenshot", text="Give a review of the establishment and upload a screenshot"),
)


class Quest(_Model):
    location: Location
    arrivalTime: str
    departureTime: str
    travelDistance: float
    task: QuestTask
    # Short model-written description of this stop; replaced by template text if unusable.
    description: str


class QuestRoute(_Model):
    startLocation: UserLocation
    quests: list[Quest]
    endLocation: UserLocation
    totalTime: int | None = None
    totalDistance: float | None = None
    estimatedCost: float | None = None
    # Present and true only when mock adapters produced this response.
    mock: Literal[True] | None = None
