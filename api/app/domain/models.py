"""Shared record shapes from docs/TEAM-CONTRACT.md draft 0.2.

These mirror the draft contract until canonical schemas exist in contracts/.
Conventions: money in integer minor units, durations in seconds, distances in
meters, instants as offset-aware datetimes. Unknown is None, never zero.
"""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Coordinates(ContractModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Money(ContractModel):
    amount_minor: StrictInt = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class Constraints(ContractModel):
    """Effective (normalized) planning input carried through the whole pipeline."""

    start: Coordinates
    departure_time: AwareDatetime
    timezone: str
    available_seconds: int
    budget: Money
    interests: list[str]
    return_to_start: bool


class DefaultApplied(ContractModel):
    field: str
    value: object


class Fact(ContractModel):
    fact_id: str
    text: str
    source_url: str
    verified_at: AwareDatetime


class OpeningInterval(ContractModel):
    opens_at: AwareDatetime
    closes_at: AwareDatetime

    @model_validator(mode="after")
    def _ordered(self) -> "OpeningInterval":
        if self.closes_at <= self.opens_at:
            raise ValueError("closes_at must be after opens_at")
        return self


class PlaceRecord(ContractModel):
    place_id: str
    business_id: str | None
    name: str
    description: str
    tags: list[str]
    coordinates: Coordinates
    timezone: str
    # None = unknown hours (cannot prove feasibility); [] = known closed.
    opening_intervals: list[OpeningInterval] | None
    estimated_cost: Money | None
    visit_seconds: int = Field(gt=0)
    facts: list[Fact]
    source_url: str
    verified_at: AwareDatetime
    publication_rights: str
    demo: bool


class Candidate(PlaceRecord):
    rank: int = Field(ge=1)
    match_reasons: list[str]


class CandidateSet(ContractModel):
    request_id: str
    retrieved_at: AwareDatetime
    ranking_version: str
    constraints: Constraints
    candidates: list[Candidate] = Field(max_length=10)
    candidate_count: int

    @model_validator(mode="after")
    def _consistent(self) -> "CandidateSet":
        if self.candidate_count != len(self.candidates):
            raise ValueError("candidate_count must equal the number of candidates")
        ids = [c.place_id for c in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError("candidates must have distinct place_id values")
        return self


class Challenge(ContractModel):
    text: str
    fact_ids: list[str]


class ProposedStop(ContractModel):
    place_id: str
    why_selected: str
    challenge: Challenge


class QuestProposal(ContractModel):
    """AI output. Untrusted until verified; totals are never accepted from it."""

    title: str
    ordered_stops: list[ProposedStop]
    planning_rationale: str


class LegEndpoint(ContractModel):
    kind: Literal["start", "stop"]
    place_id: str | None = None


class WalkingLeg(ContractModel):
    """A measured walking leg from the routing adapter, in route order."""

    from_: LegEndpoint = Field(alias="from")
    to: LegEndpoint
    walking_seconds: int = Field(ge=0)
    distance_meters: int = Field(ge=0)
    # GeoJSON LineString; coordinate pairs are [longitude, latitude].
    geometry: dict

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class ScheduledStop(ContractModel):
    place_id: str
    planned_arrival: datetime
    planned_departure: datetime
    visit_seconds: int
    estimated_cost: Money
