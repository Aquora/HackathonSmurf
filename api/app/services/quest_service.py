"""Quest generation: candidates -> planner proposal -> walking legs -> verification -> save.

At most `max_planner_calls` proposals (one initial plus one repair). A failed proposal
is PLAN_GENERATION_FAILED; NO_FEASIBLE_ROUTE is returned only when a deterministic
check over the retrieved candidates proves no three-stop route can fit.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.domain.models import Candidate, CandidateSet, Constraints, QuestProposal, WalkingLeg
from app.domain.normalization import NormalizedRequest
from app.domain.quest import (
    Completion,
    LegRef,
    PlanningInput,
    Quest,
    QuestMode,
    QuestStop,
    Route,
    RouteLeg,
)
from app.domain.verification import (
    STOP_COUNT,
    VerifiedRoute,
    Violation,
    check_selection,
    verify_route,
)
from app.errors import ApiError
from app.services.ports import (
    CandidateSource,
    DependencyError,
    Planner,
    PlannerError,
    QuestStore,
    Router,
)

CANDIDATE_LIMIT = 10


def _plannable(c: Candidate, constraints: Constraints) -> bool:
    return (
        c.opening_intervals is not None
        and c.estimated_cost is not None
        and c.estimated_cost.currency == constraints.budget.currency
        and bool(c.facts)
    )


def _open_for_visit_in_window(c: Candidate, constraints: Constraints) -> bool:
    """Some opening interval leaves room for the full visit inside the user's time window."""
    window_start = constraints.departure_time
    window_end = window_start + timedelta(seconds=constraints.available_seconds)
    return any(
        (min(i.closes_at, window_end) - max(i.opens_at, window_start)).total_seconds()
        >= c.visit_seconds
        for i in c.opening_intervals or []
    )


def _infeasibility(
    eligible: list[Candidate], constraints: Constraints
) -> tuple[str, list[dict[str, str]]] | None:
    """Sound lower-bound checks: if these fail, no choice of three candidates can fit."""
    if len(eligible) < STOP_COUNT:
        return "INSUFFICIENT_CANDIDATES", [
            {"field": "interests", "message": "Try broader or fewer interests."}
        ]
    shortest = sum(sorted(c.visit_seconds for c in eligible)[:STOP_COUNT])
    if shortest > constraints.available_seconds:
        return "TIME_BELOW_MINIMUM", [
            {
                "field": "available_seconds",
                "message": f"The three shortest visits take {shortest} seconds before walking; "
                "try allowing more time.",
            }
        ]
    eligible = [c for c in eligible if _open_for_visit_in_window(c, constraints)]
    if len(eligible) < STOP_COUNT:
        return "CLOSED_DURING_WINDOW", [
            {
                "field": "departure_time",
                "message": "Too few places are open during this time; try an earlier start.",
            }
        ]
    cheapest = sum(sorted(c.estimated_cost.amount_minor for c in eligible)[:STOP_COUNT])
    if cheapest > constraints.budget.amount_minor:
        return "BUDGET_BELOW_MINIMUM", [
            {
                "field": "budget",
                "message": f"The three lowest-cost open candidates total {cheapest} minor "
                "units; try a higher budget.",
            }
        ]
    return None


class QuestService:
    def __init__(
        self,
        candidates: CandidateSource,
        planner: Planner,
        router: Router,
        store: QuestStore,
        *,
        max_planner_calls: int = 2,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.candidates = candidates
        self.planner = planner
        self.router = router
        self.store = store
        self.max_planner_calls = max_planner_calls
        self.now = now

    def create(self, request_id: str, normalized: NormalizedRequest) -> Quest:
        constraints = normalized.constraints
        context = normalized.context()

        try:
            candidate_set = self.candidates.fetch(request_id, constraints, CANDIDATE_LIMIT)
        except DependencyError as exc:
            raise self._dependency_error("Place catalog is unavailable.", context) from exc

        eligible = [c for c in candidate_set.candidates if _plannable(c, constraints)]
        proof = _infeasibility(eligible, constraints)
        if proof:
            reason, adjustments = proof
            raise ApiError(
                422,
                "NO_FEASIBLE_ROUTE",
                "No feasible three-stop route was found in the evaluated candidate set.",
                suggested_adjustments=adjustments,
                extra_details={
                    "reason": reason,
                    "search_scope": "retrieved_candidates",
                    **context,
                },
            )

        base = PlanningInput(
            request_id=request_id, constraints=constraints, candidate_set=candidate_set
        )
        planning_input = base
        violations: list[Violation] = []
        for _ in range(self.max_planner_calls):
            legs: list[WalkingLeg] = []
            try:
                proposal = self.planner.propose(planning_input)
            except PlannerError as exc:
                violations = [Violation("PLANNER_ERROR", str(exc))]
            else:
                violations = check_selection(proposal, candidate_set)
                if not violations:
                    legs = self._walking_legs(constraints, candidate_set, proposal, context)
                    result = verify_route(constraints, candidate_set, proposal, legs)
                    if result.ok:
                        quest = self._assemble(normalized, candidate_set, proposal, result.route)
                        self.store.save(quest)
                        return quest
                    violations = result.violations
            planning_input = PlanningInput.repair_of(base, violations, legs)

        raise ApiError(
            502,
            "PLAN_GENERATION_FAILED",
            "Could not generate a valid quest. This does not mean no route exists; try again.",
            extra_details={
                "reason": "INVALID_PROPOSAL",
                "violations": [{"code": v.code, "place_id": v.place_id} for v in violations],
                **context,
            },
        )

    def _walking_legs(
        self,
        constraints: Constraints,
        candidate_set: CandidateSet,
        proposal: QuestProposal,
        context: dict,
    ) -> list[WalkingLeg]:
        by_id = {c.place_id: c for c in candidate_set.candidates}
        stops = [(s.place_id, by_id[s.place_id].coordinates) for s in proposal.ordered_stops]
        try:
            return self.router.walking_legs(constraints.start, stops, constraints.return_to_start)
        except DependencyError as exc:
            raise self._dependency_error("Walking directions are unavailable.", context) from exc

    @staticmethod
    def _dependency_error(message: str, context: dict) -> ApiError:
        return ApiError(503, "DEPENDENCY_UNAVAILABLE", message, extra_details=context)

    def _assemble(
        self,
        normalized: NormalizedRequest,
        candidate_set: CandidateSet,
        proposal: QuestProposal,
        route: VerifiedRoute,
    ) -> Quest:
        by_id = {c.place_id: c for c in candidate_set.candidates}
        stop_ids = {s.place_id: f"stop_{uuid.uuid4().hex[:12]}" for s in proposal.ordered_stops}

        stops = []
        for proposed, scheduled in zip(proposal.ordered_stops, route.stops, strict=True):
            place = by_id[proposed.place_id]
            stops.append(
                QuestStop(
                    stop_id=stop_ids[place.place_id],
                    place_id=place.place_id,
                    name=place.name,
                    coordinates=place.coordinates,
                    planned_arrival=scheduled.planned_arrival,
                    planned_departure=scheduled.planned_departure,
                    visit_seconds=scheduled.visit_seconds,
                    estimated_cost=scheduled.estimated_cost,
                    why_selected=proposed.why_selected,
                    challenge=proposed.challenge,
                    facts=place.facts,
                    place_verified_at=place.verified_at,
                    completion=Completion(),
                )
            )

        def ref(endpoint) -> LegRef:
            if endpoint.kind == "start":
                return LegRef(kind="start")
            return LegRef(kind="stop", stop_id=stop_ids[endpoint.place_id])

        legs = [
            RouteLeg(
                from_=ref(leg.from_),
                to=ref(leg.to),
                walking_seconds=leg.walking_seconds,
                distance_meters=leg.distance_meters,
                geometry=leg.geometry,
            )
            for leg in route.legs
        ]

        demo = self.candidates.demo or any(by_id[s].demo for s in stop_ids)
        return Quest(
            quest_id=f"quest_{uuid.uuid4().hex}",
            created_at=self.now(),
            constraints=normalized.constraints,
            title=proposal.title,
            stops=stops,
            route=Route(
                legs=legs,
                walking_seconds=route.walking_seconds,
                visit_seconds=route.visit_seconds,
                total_seconds=route.total_seconds,
                distance_meters=route.distance_meters,
                ends_at_start=route.ends_at_start,
            ),
            estimated_cost=route.estimated_cost,
            defaults_applied=normalized.defaults_applied,
            defaults_version=normalized.defaults_version,
            assumptions=self._assumptions(normalized, demo),
            mode=QuestMode(
                demo=demo,
                simulation=True,
                fallback_used=self.planner.template_prose,
                routing_source=self.router.source,
            ),
        )

    def _assumptions(self, normalized: NormalizedRequest, demo: bool) -> list[str]:
        notes = ["Costs are catalog estimates, not quoted prices."]
        if self.router.source == "fixture":
            notes.append("Walking times are straight-line estimates, not measured routes.")
        if demo:
            notes.append("Places are synthetic demo data, not real businesses.")
        if self.planner.template_prose:
            notes.append("Stops and challenge text come from a template planner, not the AI model.")
        if any(d.field == "start" for d in normalized.defaults_applied):
            notes.append("Start is the configured neighborhood point, not your location.")
        notes.append("Check-ins are simulated and do not redeem real offers.")
        return notes
