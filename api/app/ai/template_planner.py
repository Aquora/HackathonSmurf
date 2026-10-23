"""Deterministic stand-in for the open-weight model planner.

Picks three candidates in rank order whose catalog costs and visit times fit, orders
them nearest-neighbor from the start, and writes template prose quoting approved facts.
It is not AI: quests it produces set fallback_used. The backend still verifies them.
"""

from itertools import combinations

from app.adapters.geo import haversine_meters
from app.domain.models import Candidate, Challenge, ProposedStop, QuestProposal
from app.domain.quest import PlanningInput
from app.services.ports import PlannerError


def _nearest_neighbor(start, places: list[Candidate]) -> list[Candidate]:
    ordered, here, remaining = [], start, list(places)
    while remaining:
        nxt = min(remaining, key=lambda p: (haversine_meters(here, p.coordinates), p.place_id))
        ordered.append(nxt)
        remaining.remove(nxt)
        here = nxt.coordinates
    return ordered


def _why(place: Candidate) -> str:
    tags = [r.removeprefix("tag: ") for r in place.match_reasons if r.startswith("tag: ")]
    if tags:
        return f"Matches your interest in {', '.join(tags)}."
    return "A nearby stop that keeps the walk short."


class TemplatePlanner:
    template_prose = True
    version = "template_planner_v1"

    def propose(self, planning_input: PlanningInput) -> QuestProposal:
        c = planning_input.constraints
        excluded = {v["place_id"] for v in planning_input.previous_violations if v["place_id"]}
        previous = frozenset(
            leg.to.place_id for leg in planning_input.measured_legs if leg.to.kind == "stop"
        )
        pool = [
            p
            for p in planning_input.candidate_set.candidates
            if p.place_id not in excluded and p.estimated_cost and p.opening_intervals and p.facts
        ]

        for combo in combinations(pool, planning_input.stop_count):
            if previous and frozenset(p.place_id for p in combo) == previous:
                continue
            cost = sum(p.estimated_cost.amount_minor for p in combo)
            visits = sum(p.visit_seconds for p in combo)
            if cost <= c.budget.amount_minor and visits <= c.available_seconds:
                return self._proposal(_nearest_neighbor(c.start, list(combo)))
        raise PlannerError("No candidate combination fits the catalog costs and visit times.")

    def _proposal(self, places: list[Candidate]) -> QuestProposal:
        stops = []
        for place in places:
            fact = place.facts[0]
            stops.append(
                ProposedStop(
                    place_id=place.place_id,
                    why_selected=_why(place),
                    challenge=Challenge(
                        text=f"Spot or ask about this: {fact.text}", fact_ids=[fact.fact_id]
                    ),
                )
            )
        return QuestProposal(
            title=f"{places[0].name} to {places[-1].name}",
            ordered_stops=stops,
            planning_rationale="Template planner: rank-ordered stops that fit, nearest-first.",
        )
