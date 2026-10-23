from datetime import timedelta

from app.domain.models import Money, OpeningInterval
from app.domain.verification import verify_route
from tests.fixtures import DEPARTURE, candidate, candidate_set, constraints, legs, proposal

IDS = ["demo_place_001", "demo_place_002", "demo_place_003"]


def codes(result) -> set[str]:
    return {v.code for v in result.violations}


def run(cands=None, ids=IDS, leg_list=None, c=None, fact_ids=None):
    c = c or constraints()
    cands = cands or [candidate(n) for n in range(1, 6)]
    leg_list = leg_list if leg_list is not None else legs(ids, return_to_start=c.return_to_start)
    return verify_route(c, candidate_set(cands, c), proposal(ids, fact_ids), leg_list)


def test_feasible_route_is_recomputed_from_trusted_data():
    result = run()
    assert result.ok
    route = result.route
    assert route.walking_seconds == 3 * 300
    assert route.visit_seconds == 3 * 1200
    assert route.total_seconds == route.walking_seconds + route.visit_seconds
    assert route.estimated_cost == Money(amount_minor=2400, currency="USD")
    first, second = route.stops[0], route.stops[1]
    assert first.planned_arrival == DEPARTURE + timedelta(seconds=300)
    assert first.planned_departure == first.planned_arrival + timedelta(seconds=1200)
    assert second.planned_arrival == first.planned_departure + timedelta(seconds=300)


def test_return_leg_counts_toward_time():
    result = run(c=constraints(return_to_start=True))
    assert result.ok
    assert len(result.route.legs) == 4
    assert result.route.walking_seconds == 4 * 300
    assert result.route.ends_at_start


def test_out_of_set_duplicate_and_wrong_count_are_rejected():
    assert "UNKNOWN_PLACE" in codes(run(ids=["demo_place_001", "demo_place_002", "invented_place"]))
    assert "DUPLICATE_STOP" in codes(
        run(ids=["demo_place_001", "demo_place_001", "demo_place_002"])
    )
    assert "WRONG_STOP_COUNT" in codes(run(ids=IDS[:2]))


def test_challenge_must_cite_facts_of_its_own_place():
    other = {"demo_place_001": ["demo_place_002_fact_1"]}
    assert "UNKNOWN_FACT" in codes(run(fact_ids=other))
    assert "UNGROUNDED_CHALLENGE" in codes(run(fact_ids={"demo_place_001": []}))


def test_unknown_hours_or_cost_cannot_prove_feasibility():
    cands = [candidate(1, opening_intervals=None), candidate(2, estimated_cost=None), candidate(3)]
    assert {"UNKNOWN_HOURS", "UNKNOWN_COST"} <= codes(run(cands=cands))


def test_over_budget_is_rejected_even_by_one_cent():
    assert "OVER_BUDGET" in codes(
        run(c=constraints(budget=Money(amount_minor=2399, currency="USD")))
    )
    assert run(c=constraints(budget=Money(amount_minor=2400, currency="USD"))).ok


def test_zero_budget_only_allows_free_stops():
    c = constraints(budget=Money(amount_minor=0, currency="USD"))
    assert "OVER_BUDGET" in codes(run(c=c))
    free = [candidate(n, estimated_cost=Money(amount_minor=0, currency="USD")) for n in (1, 2, 3)]
    assert run(cands=free, c=c).ok


def test_over_time_is_rejected():
    # 3 x 1200s visits + 3 x 600s walking = 5400s fits exactly; one more second does not.
    assert run(leg_list=legs(IDS, walking_seconds=600)).ok
    assert "OVER_TIME" in codes(run(c=constraints(available_seconds=5399), leg_list=legs(IDS, 600)))


def test_place_closing_mid_visit_is_rejected():
    closes_early = [
        OpeningInterval(opens_at=DEPARTURE, closes_at=DEPARTURE + timedelta(seconds=1000))
    ]
    cands = [candidate(1, opening_intervals=closes_early), candidate(2), candidate(3)]
    result = run(cands=cands)
    assert "CLOSED_DURING_VISIT" in codes(result)
    assert all(v.place_id == "demo_place_001" for v in result.violations)


def test_known_closed_place_is_rejected():
    cands = [candidate(1, opening_intervals=[]), candidate(2), candidate(3)]
    assert "CLOSED_DURING_VISIT" in codes(run(cands=cands))


def test_currency_mismatch_is_not_silently_converted():
    cands = [
        candidate(1, estimated_cost=Money(amount_minor=100, currency="EUR")),
        candidate(2),
        candidate(3),
    ]
    assert "CURRENCY_MISMATCH" in codes(run(cands=cands))


def test_legs_must_follow_the_proposed_order():
    shuffled = legs(["demo_place_002", "demo_place_001", "demo_place_003"])
    assert "LEG_MISMATCH" in codes(run(leg_list=shuffled))
    assert "LEG_MISMATCH" in codes(run(leg_list=legs(IDS)[:2]))


def test_model_supplied_totals_are_not_accepted():
    # QuestProposal has no total fields; extra keys from a model are rejected outright.
    import pytest

    from app.domain.models import QuestProposal

    raw = proposal(IDS).model_dump()
    raw["total_cost"] = 1
    with pytest.raises(ValueError):
        QuestProposal.model_validate(raw)
