"""Quest orchestration with scripted planners and controlled adapters."""

import pytest

from app.adapters.fixture_routing import StraightLineRouter
from app.adapters.memory_store import InMemoryQuestStore
from app.domain.models import Money
from app.domain.normalization import NormalizedRequest
from app.errors import ApiError
from app.services.ports import DependencyError, PlannerError
from app.services.quest_service import QuestService
from tests.fixtures import candidate, candidate_set, constraints, legs, proposal

IDS = ["demo_place_001", "demo_place_002", "demo_place_003"]


class StaticSource:
    demo = True

    def __init__(self, cands=None, fail=False):
        self.cands = cands if cands is not None else [candidate(n) for n in range(1, 6)]
        self.fail = fail

    def fetch(self, request_id, c, limit):
        if self.fail:
            raise DependencyError("warehouse down")
        return candidate_set(self.cands[:limit], c)


class ScriptedPlanner:
    """Returns (or raises) the scripted outputs in order and records each input."""

    template_prose = False
    version = "scripted"

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.inputs = []

    def propose(self, planning_input):
        self.inputs.append(planning_input)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


class FixedRouter:
    source = "fixture"

    def __init__(self, walking_seconds=300, fail=False):
        self.walking_seconds = walking_seconds
        self.fail = fail

    def walking_legs(self, start, stops, return_to_start):
        if self.fail:
            raise DependencyError("routing down")
        return legs([pid for pid, _ in stops], self.walking_seconds, return_to_start)


def make(planner, source=None, router=None):
    store = InMemoryQuestStore()
    service = QuestService(source or StaticSource(), planner, router or FixedRouter(), store)
    return service, store


def request(**overrides):
    return NormalizedRequest(constraints(**overrides), [], "defaults_v1")


def error_of(fn) -> ApiError:
    with pytest.raises(ApiError) as exc:
        fn()
    return exc.value


def test_valid_proposal_is_saved_and_returned():
    planner = ScriptedPlanner(proposal(IDS))
    service, store = make(planner)
    quest = service.create("req_1", request())
    assert [s.place_id for s in quest.stops] == IDS
    assert store.get(quest.quest_id) == quest
    assert quest.mode.fallback_used is False
    assert len(planner.inputs) == 1
    assert planner.inputs[0].candidate_set.candidate_count == 5


def test_out_of_set_ids_get_one_repair_with_concrete_violations():
    bad = proposal(["demo_place_001", "demo_place_002", "invented_place"])
    planner = ScriptedPlanner(bad, proposal(IDS))
    service, _ = make(planner)
    quest = service.create("req_1", request())
    assert [s.place_id for s in quest.stops] == IDS
    repair = planner.inputs[1]
    assert {
        "code": "UNKNOWN_PLACE",
        "place_id": "invented_place",
    }.items() <= repair.previous_violations[0].items()


def test_infeasible_order_repair_receives_measured_legs():
    # 1500s walking per leg pushes the route over 5400s.
    planner = ScriptedPlanner(proposal(IDS), proposal(IDS))
    service, _ = make(planner, router=FixedRouter(walking_seconds=1500))
    err = error_of(lambda: service.create("req_1", request()))
    assert err.code == "PLAN_GENERATION_FAILED"
    assert err.status_code == 502
    assert {"code": "OVER_TIME", "place_id": None} in err.extra_details["violations"]
    assert len(planner.inputs[1].measured_legs) == 3
    assert err.extra_details["constraints"]["available_seconds"] == 5400


def test_repair_is_bounded_to_two_planner_calls():
    planner = ScriptedPlanner(PlannerError("timeout"), PlannerError("timeout"), proposal(IDS))
    service, store = make(planner)
    err = error_of(lambda: service.create("req_1", request()))
    assert err.code == "PLAN_GENERATION_FAILED"
    assert len(planner.inputs) == 2
    assert store._quests == {}


def test_planner_error_can_recover_on_repair():
    planner = ScriptedPlanner(PlannerError("bad json"), proposal(IDS))
    service, _ = make(planner)
    assert service.create("req_1", request()).stops


def test_fewer_than_three_plannable_candidates_is_proven_infeasible():
    cands = [candidate(1), candidate(2), candidate(3, opening_intervals=None)]
    planner = ScriptedPlanner()
    service, _ = make(planner, source=StaticSource(cands))
    err = error_of(lambda: service.create("req_1", request()))
    assert (err.code, err.extra_details["reason"]) == (
        "NO_FEASIBLE_ROUTE",
        "INSUFFICIENT_CANDIDATES",
    )
    assert planner.inputs == []


def test_budget_below_cheapest_three_is_proven_infeasible():
    service, _ = make(ScriptedPlanner())
    c = request(budget=Money(amount_minor=2399, currency="USD"))
    err = error_of(lambda: service.create("req_1", c))
    assert err.extra_details["reason"] == "BUDGET_BELOW_MINIMUM"
    assert err.extra_details["search_scope"] == "retrieved_candidates"


def test_places_closed_during_the_window_are_proven_infeasible():
    from datetime import timedelta

    from app.domain.models import OpeningInterval
    from tests.fixtures import DEPARTURE

    # Closes 10 minutes into the window; a 20-minute visit can never fit.
    short = [OpeningInterval(opens_at=DEPARTURE, closes_at=DEPARTURE + timedelta(minutes=10))]
    cands = [candidate(1, opening_intervals=short), candidate(2), candidate(3)]
    planner = ScriptedPlanner()
    service, _ = make(planner, source=StaticSource(cands))
    err = error_of(lambda: service.create("req_1", request()))
    assert err.extra_details["reason"] == "CLOSED_DURING_WINDOW"
    assert planner.inputs == []


def test_empty_candidate_set_is_not_a_dependency_failure():
    service, _ = make(ScriptedPlanner(), source=StaticSource([]))
    assert error_of(lambda: service.create("req_1", request())).code == "NO_FEASIBLE_ROUTE"


def test_warehouse_and_routing_failures_are_dependency_errors():
    service, _ = make(ScriptedPlanner(), source=StaticSource(fail=True))
    assert error_of(lambda: service.create("req_1", request())).code == "DEPENDENCY_UNAVAILABLE"

    service, _ = make(ScriptedPlanner(proposal(IDS)), router=FixedRouter(fail=True))
    err = error_of(lambda: service.create("req_1", request()))
    assert (err.code, err.status_code) == ("DEPENDENCY_UNAVAILABLE", 503)


def test_return_to_start_adds_a_final_leg_back_to_start():
    service, _ = make(ScriptedPlanner(proposal(IDS)))
    quest = service.create("req_1", request(return_to_start=True))
    assert len(quest.route.legs) == 4
    assert quest.route.legs[-1].to.kind == "start"
    assert quest.route.ends_at_start


def test_straight_line_router_geometry_is_lon_lat():
    from app.domain.models import Coordinates

    start = Coordinates(latitude=34.05, longitude=-117.75)
    stop = Coordinates(latitude=34.06, longitude=-117.74)
    (leg,) = StraightLineRouter().walking_legs(start, [("p1", stop)], False)
    assert leg.geometry["coordinates"] == [[-117.75, 34.05], [-117.74, 34.06]]
    assert leg.distance_meters > 1000
    assert leg.walking_seconds > 0
