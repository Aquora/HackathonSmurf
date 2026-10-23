"""Deterministic verification of an AI quest proposal.

The AI only selects and orders candidate IDs. This module recomputes the
schedule, costs, and durations from trusted catalog records and measured walking
legs, and reports every rule the proposal breaks. Violations are structured so a
single bounded repair request can cite them.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from app.domain.models import (
    Candidate,
    CandidateSet,
    Constraints,
    Money,
    QuestProposal,
    ScheduledStop,
    WalkingLeg,
)

STOP_COUNT = 3


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    place_id: str | None = None


@dataclass(frozen=True)
class VerifiedRoute:
    stops: list[ScheduledStop]
    legs: list[WalkingLeg]
    walking_seconds: int
    visit_seconds: int
    total_seconds: int
    distance_meters: int
    estimated_cost: Money
    ends_at_start: bool


@dataclass
class VerificationResult:
    violations: list[Violation] = field(default_factory=list)
    route: VerifiedRoute | None = None

    @property
    def ok(self) -> bool:
        return not self.violations and self.route is not None


def check_selection(proposal: QuestProposal, candidate_set: CandidateSet) -> list[Violation]:
    """Schema-level checks to run before requesting walking directions."""
    violations: list[Violation] = []
    by_id = {c.place_id: c for c in candidate_set.candidates}
    ids = [s.place_id for s in proposal.ordered_stops]

    if len(ids) != STOP_COUNT:
        violations.append(
            Violation("WRONG_STOP_COUNT", f"Expected {STOP_COUNT} stops, got {len(ids)}.")
        )
    if len(set(ids)) != len(ids):
        violations.append(Violation("DUPLICATE_STOP", "Each stop must be a different place."))

    for stop in proposal.ordered_stops:
        place = by_id.get(stop.place_id)
        if place is None:
            violations.append(
                Violation("UNKNOWN_PLACE", "Place is not in the candidate set.", stop.place_id)
            )
            continue
        fact_ids = {f.fact_id for f in place.facts}
        if not stop.challenge.fact_ids:
            violations.append(
                Violation("UNGROUNDED_CHALLENGE", "Challenge cites no facts.", stop.place_id)
            )
        for fact_id in stop.challenge.fact_ids:
            if fact_id not in fact_ids:
                violations.append(
                    Violation(
                        "UNKNOWN_FACT",
                        f"Fact {fact_id} does not belong to this place.",
                        stop.place_id,
                    )
                )
        if place.opening_intervals is None:
            violations.append(
                Violation("UNKNOWN_HOURS", "Opening hours are unknown.", stop.place_id)
            )
        if place.estimated_cost is None:
            violations.append(
                Violation("UNKNOWN_COST", "Estimated cost is unknown.", stop.place_id)
            )
    return violations


def _check_legs(ids: list[str], legs: list[WalkingLeg], return_to_start: bool) -> list[Violation]:
    expected = [("start", None)] + [("stop", pid) for pid in ids]
    if return_to_start:
        expected.append(("start", None))
    pairs = list(zip(expected, expected[1:], strict=False))
    if len(legs) != len(pairs):
        return [Violation("LEG_MISMATCH", f"Expected {len(pairs)} walking legs, got {len(legs)}.")]
    violations = []
    for i, (leg, (frm, to)) in enumerate(zip(legs, pairs, strict=True)):
        if (leg.from_.kind, leg.from_.place_id) != frm or (leg.to.kind, leg.to.place_id) != to:
            violations.append(
                Violation("LEG_MISMATCH", f"Walking leg {i} does not follow the stop order.")
            )
    return violations


def _within_opening_hours(place: Candidate, arrival, departure) -> bool:
    return any(
        interval.opens_at <= arrival and departure <= interval.closes_at
        for interval in place.opening_intervals or []
    )


def verify_route(
    constraints: Constraints,
    candidate_set: CandidateSet,
    proposal: QuestProposal,
    legs: list[WalkingLeg],
) -> VerificationResult:
    """Full check of a proposal against measured legs. Returns a route only if all rules pass."""
    violations = check_selection(proposal, candidate_set)
    if violations:
        return VerificationResult(violations)

    by_id = {c.place_id: c for c in candidate_set.candidates}
    ids = [s.place_id for s in proposal.ordered_stops]
    violations = _check_legs(ids, legs, constraints.return_to_start)
    if violations:
        return VerificationResult(violations)

    budget = constraints.budget
    clock = constraints.departure_time
    stops: list[ScheduledStop] = []
    cost_total = 0
    visit_total = 0

    for pid, leg in zip(ids, legs, strict=False):
        place = by_id[pid]
        cost = place.estimated_cost
        if cost.currency != budget.currency:
            violations.append(
                Violation("CURRENCY_MISMATCH", "Cost is in a different currency.", pid)
            )
        arrival = clock + timedelta(seconds=leg.walking_seconds)
        departure = arrival + timedelta(seconds=place.visit_seconds)
        if not _within_opening_hours(place, arrival, departure):
            violations.append(
                Violation(
                    "CLOSED_DURING_VISIT", "Place is not open for the whole planned visit.", pid
                )
            )
        stops.append(
            ScheduledStop(
                place_id=pid,
                planned_arrival=arrival,
                planned_departure=departure,
                visit_seconds=place.visit_seconds,
                estimated_cost=cost,
            )
        )
        cost_total += cost.amount_minor
        visit_total += place.visit_seconds
        clock = departure

    walking_total = sum(leg.walking_seconds for leg in legs)
    total_seconds = walking_total + visit_total
    if cost_total > budget.amount_minor:
        violations.append(
            Violation(
                "OVER_BUDGET", f"Estimated cost {cost_total} exceeds budget {budget.amount_minor}."
            )
        )
    if total_seconds > constraints.available_seconds:
        violations.append(
            Violation(
                "OVER_TIME",
                f"Walking plus visits take {total_seconds}s; "
                f"{constraints.available_seconds}s available.",
            )
        )
    if violations:
        return VerificationResult(violations)

    route = VerifiedRoute(
        stops=stops,
        legs=legs,
        walking_seconds=walking_total,
        visit_seconds=visit_total,
        total_seconds=total_seconds,
        distance_meters=sum(leg.distance_meters for leg in legs),
        estimated_cost=Money(amount_minor=cost_total, currency=budget.currency),
        ends_at_start=constraints.return_to_start,
    )
    return VerificationResult(route=route)
