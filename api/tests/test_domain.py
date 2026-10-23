import json

import pytest

from app.adapters.mock.mock_adapters import MOCK_LOCATIONS
from app.domain.locations import parse_locations
from app.domain.preferences import normalize_preferences
from app.domain.route import RouteContext, validate_route

DEFAULTS = {"desiredTime": 90, "desiredBudget": 30, "locationPreference": "random", "travelMethod": "drive"}
COFFEE = MOCK_LOCATIONS[0]  # closes 18:00
MUSEUM = MOCK_LOCATIONS[5]  # closes 16:30
ARCADE = MOCK_LOCATIONS[9]  # closes 23:59
CTX = RouteContext(address="1 Home St", candidates=MOCK_LOCATIONS, start_time="10:00")


def quest(loc, arrival, departure, distance=1.234):
    location = loc.model_dump() if hasattr(loc, "model_dump") else loc
    return {"location": location, "arrivalTime": arrival, "departureTime": departure, "travelDistance": distance}


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
        rows = [{"NAME": l.name, "ADDRESS": l.address, "CLOSING_TIME": f"{l.closingTime}:00"} for l in MOCK_LOCATIONS]
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
            "quests": [{"location": COFFEE.model_dump(), "arrivalTime": "10:10", "departureTime": "10:40", "travelDistance": 1.23}],
            "endLocation": {"address": "1 Home St"},
            "totalTime": 60,
            "estimatedCost": 12.35,
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
        ctx = RouteContext(address="1 Home St", candidates=MOCK_LOCATIONS, start_time="17:00")
        assert not validate_route({"quests": [quest(MUSEUM, "17:10", "17:30")]}, ctx).ok

    def test_midnight_handling(self):
        ctx = RouteContext(address="1 Home St", candidates=MOCK_LOCATIONS, start_time="23:00")
        assert validate_route({"quests": [quest(ARCADE, "23:10", "23:50")]}, ctx).ok
        assert not validate_route({"quests": [quest(ARCADE, "23:30", "00:10")]}, ctx).ok

    def test_schema_violations(self):
        assert not validate_route({"quests": [quest(COFFEE, "10:10", "10:40", distance=-1)]}, CTX).ok
        assert not validate_route("garbage", CTX).ok
        assert not validate_route({"quests": [quest(COFFEE, "10:10", "10:40")] * 11}, CTX).ok
