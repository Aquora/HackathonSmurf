"""Interfaces the quest service depends on. Fixture and live adapters implement them."""

from typing import Literal, Protocol

from app.domain.models import CandidateSet, Constraints, Coordinates, QuestProposal, WalkingLeg
from app.domain.quest import PlanningInput, Quest


class DependencyError(Exception):
    """A required provider (warehouse, routing) could not complete the operation."""


class PlannerError(Exception):
    """The model failed or returned output that does not parse as a QuestProposal."""


class CandidateSource(Protocol):
    demo: bool

    def fetch(self, request_id: str, constraints: Constraints, limit: int) -> CandidateSet: ...


class Planner(Protocol):
    # True when prose comes from templates rather than a model (sets fallback_used).
    template_prose: bool
    version: str

    def propose(self, planning_input: PlanningInput) -> QuestProposal: ...


class Router(Protocol):
    source: Literal["provider", "cache", "fixture"]

    def walking_legs(
        self, start: Coordinates, stops: list[tuple[str, Coordinates]], return_to_start: bool
    ) -> list[WalkingLeg]: ...


class QuestStore(Protocol):
    def save(self, quest: Quest) -> None: ...

    def get(self, quest_id: str) -> Quest | None: ...
