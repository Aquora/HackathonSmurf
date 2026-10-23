"""Planner input and the frontend Quest response (docs/TEAM-CONTRACT.md §5, §7)."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.domain.models import (
    CandidateSet,
    Challenge,
    Constraints,
    ContractModel,
    Coordinates,
    DefaultApplied,
    Fact,
    Money,
    WalkingLeg,
)
from app.domain.verification import Violation

OBJECTIVE = "Satisfy hard constraints, prefer interest matches, and reduce walking."


class PlanningInput(ContractModel):
    request_id: str
    constraints: Constraints
    candidate_set: CandidateSet
    stop_count: int = 3
    objective: str = OBJECTIVE
    # Present only on the single repair attempt.
    previous_violations: list[dict[str, str | None]] = Field(default_factory=list)
    measured_legs: list[WalkingLeg] = Field(default_factory=list)

    @classmethod
    def repair_of(
        cls, base: "PlanningInput", violations: list[Violation], legs: list[WalkingLeg]
    ) -> "PlanningInput":
        return base.model_copy(
            update={
                "previous_violations": [
                    {"code": v.code, "message": v.message, "place_id": v.place_id}
                    for v in violations
                ],
                "measured_legs": legs,
            }
        )


class Completion(ContractModel):
    status: Literal["pending", "completed"] = "pending"
    completed_at: datetime | None = None


class QuestStop(ContractModel):
    stop_id: str
    place_id: str
    name: str
    coordinates: Coordinates
    planned_arrival: datetime
    planned_departure: datetime
    visit_seconds: int
    estimated_cost: Money
    why_selected: str
    challenge: Challenge
    facts: list[Fact]
    place_verified_at: datetime
    completion: Completion


class LegRef(ContractModel):
    kind: Literal["start", "stop"]
    stop_id: str | None = None


class RouteLeg(ContractModel):
    from_: LegRef = Field(alias="from")
    to: LegRef
    walking_seconds: int
    distance_meters: int
    geometry: dict

    model_config = ContractModel.model_config | {"populate_by_name": True}


class Route(ContractModel):
    legs: list[RouteLeg]
    walking_seconds: int
    visit_seconds: int
    total_seconds: int
    distance_meters: int
    ends_at_start: bool


class QuestMode(ContractModel):
    demo: bool
    simulation: bool
    fallback_used: bool
    routing_source: Literal["provider", "cache", "fixture"]


class Quest(ContractModel):
    quest_id: str
    created_at: datetime
    constraints: Constraints
    title: str
    stops: list[QuestStop]
    route: Route
    estimated_cost: Money
    defaults_applied: list[DefaultApplied]
    defaults_version: str
    assumptions: list[str]
    mode: QuestMode
