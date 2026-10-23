"""Quest request validation and missing-input defaults.

Omitted optional fields get the configured defaults and are disclosed in
defaults_applied. Explicit nulls, malformed values, and unsupported currencies are
validation errors; a valid override (including a $0 budget or an empty interests
list) is preserved and never replaced by a default.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

from app.config import Settings
from app.domain.models import Constraints, Coordinates, DefaultApplied, Money
from app.errors import configuration_error, validation_error


class QuestRequest(BaseModel):
    """POST /v1/quests body. Every field is optional; null is never allowed."""

    model_config = ConfigDict(extra="forbid")

    start: Coordinates | None = None
    departure_time: AwareDatetime | None = None
    timezone: StrictStr | None = None
    available_seconds: StrictInt | None = Field(default=None, gt=0)
    budget: Money | None = None
    interests: list[StrictStr] | None = None
    return_to_start: StrictBool | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_null(cls, data: Any) -> Any:
        if isinstance(data, dict):
            nulls = [key for key, value in data.items() if value is None]
            if nulls:
                raise ValueError(f"null is not allowed; omit the field instead: {', '.join(nulls)}")
        return data


@dataclass(frozen=True)
class NormalizedRequest:
    constraints: Constraints
    defaults_applied: list[DefaultApplied]
    defaults_version: str

    def context(self) -> dict[str, Any]:
        """Normalization context attached to responses and post-normalization errors."""
        return {
            "constraints": self.constraints.model_dump(mode="json"),
            "defaults_applied": [d.model_dump(mode="json") for d in self.defaults_applied],
            "defaults_version": self.defaults_version,
        }


def _zone(name: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def normalize(request: QuestRequest, settings: Settings) -> NormalizedRequest:
    field_errors: list[dict[str, str]] = []
    applied: list[DefaultApplied] = []
    supplied = request.model_fields_set

    # Duration
    if "available_seconds" in supplied:
        available_seconds = request.available_seconds
        if available_seconds > settings.max_available_seconds:
            field_errors.append(
                {
                    "field": "available_seconds",
                    "message": f"Must be at most {settings.max_available_seconds} seconds.",
                }
            )
    else:
        available_seconds = settings.default_available_seconds
        applied.append(DefaultApplied(field="available_seconds", value=available_seconds))

    # Budget (treated as a unit; partial objects already fail model validation)
    accepted = settings.accepted_currencies()
    if not accepted:
        raise configuration_error("No budget currency is configured.")
    if "budget" in supplied:
        budget = request.budget
        if budget.currency not in accepted:
            field_errors.append({"field": "budget.currency", "message": "Unsupported currency."})
        if budget.amount_minor > settings.max_budget_amount_minor:
            field_errors.append(
                {
                    "field": "budget.amount_minor",
                    "message": f"Must be at most {settings.max_budget_amount_minor}.",
                }
            )
    else:
        budget = None

    # Interests: trim, lowercase, de-duplicate in order. [] means no preference.
    if "interests" in supplied:
        interests: list[str] = []
        if len(request.interests) > settings.max_interests:
            field_errors.append(
                {
                    "field": "interests",
                    "message": f"At most {settings.max_interests} interests are allowed.",
                }
            )
        for i, raw in enumerate(request.interests):
            value = raw.strip().lower()
            if not value or len(value) > settings.max_interest_length:
                field_errors.append(
                    {
                        "field": f"interests.{i}",
                        "message": f"Must be 1-{settings.max_interest_length} characters.",
                    }
                )
            elif value not in interests:
                interests.append(value)
    else:
        interests = []
        applied.append(DefaultApplied(field="interests", value=[]))

    # Timezone
    timezone = request.timezone
    if "timezone" in supplied:
        if _zone(timezone) is None:
            field_errors.append({"field": "timezone", "message": "Unknown IANA timezone."})
            timezone = None
    elif settings.default_timezone:
        timezone = settings.default_timezone
        applied.append(DefaultApplied(field="timezone", value=timezone))

    # Departure time must agree with the timezone's offset at that instant.
    departure_time: datetime | None = request.departure_time
    if departure_time is not None and timezone is not None and (zone := _zone(timezone)):
        if departure_time.utcoffset() != departure_time.astimezone(zone).utcoffset():
            field_errors.append(
                {
                    "field": "departure_time",
                    "message": f"Offset does not match {timezone} at that time.",
                }
            )

    return_to_start = request.return_to_start
    if "return_to_start" not in supplied:
        return_to_start = False
        applied.append(DefaultApplied(field="return_to_start", value=False))

    if field_errors:
        raise validation_error(field_errors)

    # Fallbacks that depend on unresolved policy: fail explicitly, never guess.
    if budget is None:
        if not settings.default_currency:
            raise configuration_error("Default budget currency is not configured.")
        budget = Money(
            amount_minor=settings.default_budget_amount_minor,
            currency=settings.default_currency,
        )
        applied.append(DefaultApplied(field="budget", value=budget.model_dump()))

    start = request.start
    if start is None:
        lat = settings.neighborhood_anchor_latitude
        lon = settings.neighborhood_anchor_longitude
        if lat is None or lon is None:
            raise configuration_error("No starting location was given and no fallback is set.")
        start = Coordinates(latitude=lat, longitude=lon)
        applied.append(DefaultApplied(field="start", value=start.model_dump()))

    if timezone is None:
        raise configuration_error("No timezone was given and no default timezone is configured.")
    if departure_time is None:
        raise configuration_error("No departure time was given and no fallback policy is set.")

    constraints = Constraints(
        start=start,
        departure_time=departure_time,
        timezone=timezone,
        available_seconds=available_seconds,
        budget=budget,
        interests=interests,
        return_to_start=return_to_start,
    )
    return NormalizedRequest(constraints, applied, settings.defaults_version)
