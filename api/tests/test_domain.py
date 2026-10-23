import json

import pytest

from app.adapters.mock.mock_adapters import MOCK_LOCATIONS
from app.domain.locations import parse_locations
from app.domain.preferences import normalize_preferences
from app.domain.locations import location_key
from app.domain.route import RouteContext, prove_infeasible, validate_route
from app.domain.tasks import DESCRIPTION_MAX_LENGTH, assign_tasks
from app.domain.types import QUEST_TASKS, Location

DEFAULTS = {"desiredTime": 90, "desiredBudget": 30, "locationPreference": "random", "travelMethod": "drive"}
COFFEE = MOCK_LOCATIONS[0]  # closes 18:00
MUSEUM = MOCK_LOCATIONS[5]  # closes 16:30
ARCADE = MOCK_LOCATIONS[9]  # closes 23:59
# Generous limits so tests of other rules are not tripped by time or budget.
# Every location gets the "inside photo" task so outputs are deterministic.
LIMITS = {
    "desired_time": 24 * 60,
    "desired_budget": 1000.0,
    "tasks": {location_key(l.name, l.address): QUEST_TASKS[0] for l in MOCK_LOCATIONS},
}
CTX = RouteContext(address="1 Home St", candidates=MOCK_LOCATIONS, start_time="10:00", **LIMITS)


def quest(loc, arrival, departure, distance=1.234, description="A fun stop."):
    location = loc.model_dump() if hasattr(loc, "model_dump") else loc
    return {
        "location": location,
        "arrivalTime": arrival,
        "departureTime": departure,
        "travelDistance": distance,
        "description": description,
    }


class TestNormalizePreferences:
    @pytest.mark.parametrize(
        "raw",
        [None, "nope", [], {}, {"desiredTime": None, "desiredBudget": None, "locationPreference": None, "travelMethod": None}],
    )
    def test_defaults_for_missing_input(self, raw):
        assert normalize_preferences(raw).model_dump() == DEFAULTS

    def test_keeps_valid_values_and_coerces(self):
        p = normalize_preferences(
            {"desiredTime": "120 minutes", "desiredBudget": "$45.50", "locationPreference": "  coffee,  art ", "travelMethod": "Walking"}
        )
        assert p.model_dump() == {"desiredTime": 120, "desiredBudget": 45.5, "locationPreference": "coffee, art", "travelMethod": "walk"}

    def test_zero_budget_allowed_zero_time_rejected(self):
        p = normalize_preferences({"desiredTime": 0, "desiredBudget": 0})
        assert (p.desiredTime, p.desiredBudget) == (90, 0)

    def test_out_of_range_and_wrong_types(self):
        p = normalize_preferences({"desiredTime": -5, "desiredBudget": float("inf"), "locationPreference": 42, "travelMethod": ""})
        assert p.model_dump() == DEFAULTS
        assert normalize_preferences({"desiredTime": 100_000}).desiredTime == 90
        assert normalize_preferences({"desiredTime": True}).desiredTime == 90
        assert normalize_preferences({"locationPreference": "x" * 500}).locationPreference == "random"

    def test_unknown_travel_method_passes_through_lowercased(self):
        assert normalize_preferences({"travelMethod": "Scooter"}).travelMethod == "scooter"


class TestParseLocations:
    def test_accepts_snowflake_shape(self):
        rows = [
            {"NAME": l.name, "ADDRESS": l.address, "CLOSING_TIME": f"{l.closingTime}:00", "ESTIMATED_COST": l.estimatedCost}
            for l in MOCK_LOCATIONS
        ]
        result = parse_locations(json.dumps({"locations": rows}))
        assert result.ok and result.locations == MOCK_LOCATIONS

    def test_rejects_wrong_count(self):
        result = parse_locations([l.model_dump() for l in MOCK_LOCATIONS[:9]])
        assert not result.ok and "exactly 10" in result.issues[0]

    def test_rejects_duplicates_and_missing_fields(self):
        dup = [l.model_dump() for l in MOCK_LOCATIONS[:9]] + [MOCK_LOCATIONS[0].model_dump()]
        assert "duplicates" in parse_locations(dup).issues[0]
        missing = [l.model_dump() for l in MOCK_LOCATIONS[:9]] + [{"name": "X", "address": ""}]
        issues = "\n".join(parse_locations(missing).issues)
        assert "address is missing" in issues and "closingTime is missing" in issues
        assert not parse_locations("not json").ok


class TestValidateRoute:
    def test_forces_home_address_and_canonical_records(self):
        fake_closing = {"name": COFFEE.name.upper(), "address": COFFEE.address, "closingTime": "99:99"}
        result = validate_route(
            {
                "startLocation": {"address": "elsewhere"},
                "endLocation": {"address": "elsewhere"},
                "quests": [quest(fake_closing, "10:10", "10:40")],
                "totalTime": 60.4,
                "estimatedCost": 12.345,
            },
            CTX,
        )
        assert result.ok
        assert result.route.model_dump(exclude_none=True) == {
            "startLocation": {"address": "1 Home St"},
            "quests": [
                {
                    "location": COFFEE.model_dump(),
                    "arrivalTime": "10:10",
                    "departureTime": "10:40",
                    "travelDistance": 1.23,
                    "task": QUEST_TASKS[0].model_dump(),
                    "description": "A fun stop.",
                }
            ],
            "endLocation": {"address": "1 Home St"},
            "totalTime": 60,
            "estimatedCost": 6.0,
        }

    def test_unwraps_route_envelope(self):
        assert validate_route({"route": {"quests": [quest(COFFEE, "10:10", "10:40")]}}, CTX).ok

    def test_rejects_invented_duplicate_and_closed(self):
        result = validate_route(
            {
                "quests": [
                    quest({"name": "Made Up Cafe", "address": "1 Nowhere"}, "10:10", "10:20"),
                    quest(COFFEE, "10:30", "10:50"),
                    quest(COFFEE, "11:00", "11:10"),
                    quest(MUSEUM, "16:00", "17:00"),
                ]
            },
            CTX,
        )
        issues = "\n".join(result.issues)
        assert not result.ok
        assert 'Made Up Cafe" is not one of the provided' in issues
        assert "appears more than once" in issues
        assert "past its closing time 16:30" in issues

    def test_rejects_out_of_order_and_malformed_times(self):
        result = validate_route({"quests": [quest(COFFEE, "11:00", "10:30"), quest(MUSEUM, "10:45", "11:00")]}, CTX)
        issues = "\n".join(result.issues)
        assert "departureTime is before its arrivalTime" in issues
        assert "before the previous departure" in issues
        assert len(validate_route({"quests": [quest(COFFEE, "noon", "1pm")]}, CTX).issues) == 2

    def test_place_closed_before_start_is_closed(self):
        ctx = RouteContext(address="1 Home St", candidates=MOCK_LOCATIONS, start_time="17:00", **LIMITS)
        assert not validate_route({"quests": [quest(MUSEUM, "17:10", "17:30")]}, ctx).ok

    def test_midnight_handling(self):
        ctx = RouteContext(address="1 Home St", candidates=MOCK_LOCATIONS, start_time="23:00", **LIMITS)
        assert validate_route({"quests": [quest(ARCADE, "23:10", "23:50")]}, ctx).ok
        assert not validate_route({"quests": [quest(ARCADE, "23:30", "00:10")]}, ctx).ok

    def test_schema_violations(self):
        assert not validate_route({"quests": [quest(COFFEE, "10:10", "10:40", distance=-1)]}, CTX).ok
        assert not validate_route("garbage", CTX).ok
        assert not validate_route({"quests": [quest(COFFEE, "10:10", "10:40")] * 11}, CTX).ok


def ctx(**overrides) -> RouteContext:
    base = {"address": "1 Home St", "candidates": MOCK_LOCATIONS, "start_time": "10:00", **LIMITS}
    return RouteContext(**{**base, **overrides})


GALLERY = MOCK_LOCATIONS[1]  # $0, closes 17:00
BOOKSHOP = MOCK_LOCATIONS[3]  # $15


class TestBudgetAndTimeInCode:
    def test_cost_is_summed_from_catalog_not_model(self):
        route = {"quests": [quest(COFFEE, "10:10", "10:30"), quest(BOOKSHOP, "10:40", "11:00")], "estimatedCost": 1}
        result = validate_route(route, ctx(desired_budget=25))
        assert result.ok and result.route.estimatedCost == 21.0

    def test_over_budget_is_rejected(self):
        route = {"quests": [quest(COFFEE, "10:10", "10:30"), quest(BOOKSHOP, "10:40", "11:00")], "estimatedCost": 5}
        result = validate_route(route, ctx(desired_budget=20.99))
        assert not result.ok and "over the $20.99 budget" in result.issues[0]

    def test_zero_budget_allows_free_stops_only(self):
        assert validate_route({"quests": [quest(GALLERY, "10:10", "10:30")]}, ctx(desired_budget=0)).ok
        assert not validate_route({"quests": [quest(COFFEE, "10:10", "10:30")]}, ctx(desired_budget=0)).ok

    def test_unknown_cost_cannot_prove_budget(self):
        mystery = Location(name="Mystery Spot", address="1 Unknown Rd", closingTime="20:00")
        candidates = [*MOCK_LOCATIONS[:9], mystery]
        result = validate_route({"quests": [quest(mystery, "10:10", "10:30")]}, ctx(candidates=candidates))
        assert not result.ok and "no known cost" in result.issues[0]

    def test_stops_running_past_time_limit_are_rejected(self):
        route = {"quests": [quest(COFFEE, "10:10", "11:00"), quest(GALLERY, "11:10", "11:40")]}
        assert validate_route(route, ctx(desired_time=100)).ok
        result = validate_route(route, ctx(desired_time=99))
        assert not result.ok and "over the 99-minute limit" in result.issues[0]

    def test_model_total_time_must_fit_and_be_consistent(self):
        stops = [quest(COFFEE, "10:10", "11:00")]
        assert "exceeds the 90-minute limit" in validate_route({"quests": stops, "totalTime": 95}, ctx(desired_time=90)).issues[0]
        assert "shorter than the 60 minutes" in validate_route({"quests": stops, "totalTime": 30}, ctx(desired_time=90)).issues[0]

    def test_arrival_before_start_cannot_hide_inside_time_limit(self):
        # 09:50 wraps to nearly a full day after a 10:00 start.
        assert not validate_route({"quests": [quest(COFFEE, "09:50", "09:55")]}, ctx(desired_time=90)).ok


class TestProveInfeasible:
    def test_feasible_candidates_have_no_proof(self):
        assert prove_infeasible(ctx(desired_budget=30)) is None

    def test_all_closed_is_proven(self):
        late = ctx(start_time="23:59", candidates=[l for l in MOCK_LOCATIONS if l.closingTime != "23:59"])
        assert prove_infeasible(late).reason == "ALL_CLOSED"

    def test_nothing_affordable_is_proven(self):
        priced = [l.model_copy(update={"estimatedCost": 5}) for l in MOCK_LOCATIONS]
        assert prove_infeasible(ctx(candidates=priced, desired_budget=4.99)).reason == "NONE_WITHIN_BUDGET"
        unknown = [l.model_copy(update={"estimatedCost": None}) for l in MOCK_LOCATIONS]
        assert prove_infeasible(ctx(candidates=unknown, desired_budget=100)).reason == "NONE_WITHIN_BUDGET"

    def test_affordable_place_that_is_closed_does_not_count(self):
        # At 17:30 the free gallery (closes 17:00) is closed; everything open costs more than $5.
        assert prove_infeasible(ctx(start_time="17:30", desired_budget=5)) is None  # park is free and open
        no_park = [l for l in MOCK_LOCATIONS if l.name != "Demo Lookout Park"]
        assert prove_infeasible(ctx(start_time="17:30", desired_budget=5, candidates=no_park)).reason == "NONE_WITHIN_BUDGET"


class TestParseCosts:
    def test_reads_snowflake_cost_and_treats_missing_as_unknown(self):
        rows = [{"NAME": l.name, "ADDRESS": l.address, "CLOSING_TIME": l.closingTime, "ESTIMATED_COST": "6.50"} for l in MOCK_LOCATIONS]
        del rows[1]["ESTIMATED_COST"]
        result = parse_locations(rows)
        assert result.ok
        assert result.locations[0].estimatedCost == 6.5 and result.locations[1].estimatedCost is None

    @pytest.mark.parametrize("bad", [-1, "free", True, float("nan")])
    def test_rejects_unusable_costs(self, bad):
        rows = [l.model_dump() for l in MOCK_LOCATIONS]
        rows[0]["estimatedCost"] = bad
        assert "estimatedCost must be a non-negative number" in parse_locations(rows).issues[0]


class TestTasksAndDescriptions:
    def test_assign_tasks_gives_every_location_one_of_the_three(self):
        import random

        tasks = assign_tasks(MOCK_LOCATIONS, random.Random(1))
        assert set(tasks) == {location_key(l.name, l.address) for l in MOCK_LOCATIONS}
        assert set(tasks.values()) <= set(QUEST_TASKS)
        # Over many locations all three tasks show up (seeded, so stable).
        many = [Location(name=f"P{i}", address=f"{i} St", closingTime="20:00") for i in range(60)]
        assert set(assign_tasks(many, random.Random(1)).values()) == set(QUEST_TASKS)

    def test_code_assigned_task_wins_over_the_models(self):
        review = QUEST_TASKS[2]
        c = ctx(tasks={location_key(COFFEE.name, COFFEE.address): review})
        stop = quest(COFFEE, "10:10", "10:40") | {"task": QUEST_TASKS[1].model_dump()}  # model picked a different one
        result = validate_route({"quests": [stop]}, c)
        assert result.ok and result.route.quests[0].task == review

    def test_unassigned_location_still_gets_a_valid_task(self):
        result = validate_route({"quests": [quest(COFFEE, "10:10", "10:40")]}, ctx(tasks={}))
        assert result.ok and result.route.quests[0].task in QUEST_TASKS

    def test_description_is_cleaned(self):
        result = validate_route({"quests": [quest(COFFEE, "10:10", "10:40", description="  Grab a\n coffee!  ")]}, CTX)
        assert result.route.quests[0].description == "Grab a coffee!"

    @pytest.mark.parametrize("bad", [None, "", "   ", 42, "x" * (DESCRIPTION_MAX_LENGTH + 1)])
    def test_unusable_description_falls_back_without_failing(self, bad):
        result = validate_route({"quests": [quest(COFFEE, "10:10", "10:40", description=bad)]}, CTX)
        assert result.ok
        assert result.route.quests[0].description == (
            f"Stop by {COFFEE.name} at {COFFEE.address}. Your task: Take a picture of the inside."
        )
