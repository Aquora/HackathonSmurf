from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.adapters.mock.mock_adapters import MOCK_LOCATIONS, MockLocationProvider, MockPreferenceExtractor, MockRoutePlanner
from app.domain.types import DEFAULT_START_ADDRESS, UserLocation, UserRequest
from app.errors import AppError, upstream_unavailable
from app.main import FixedWindowRateLimiter, create_app
from app.services.quest_service import QuestService, local_clock

# 2026-10-23 17:00Z = 10:00 in America/Los_Angeles (PDT).
NOW = datetime(2026, 10, 23, 17, 0, tzinfo=UTC)
TZ = "America/Los_Angeles"
ADDRESS = "1 Home St, Demo City, CA 90000"
BODY = {"message": "I have 2 hours and $25, want coffee and art, walking", "location": {"address": ADDRESS}}
REQUEST = UserRequest.model_validate(BODY)


def make_service(extractor=None, locations=None, planner=None, mock=False) -> QuestService:
    return QuestService(
        extractor=extractor or MockPreferenceExtractor(),
        locations=locations or MockLocationProvider(),
        planner=planner or MockRoutePlanner(),
        timezone=TZ,
        mock=mock,
        now=lambda: NOW,
    )


def client(service=None, rate_limit=100) -> TestClient:
    app = create_app(service or make_service(), cors_origins=["http://localhost:3000"], rate_limit_per_minute=rate_limit)
    return TestClient(app, raise_server_exceptions=False)


def test_local_clock():
    assert local_clock(NOW, TZ) == "10:00"
    assert local_clock(datetime(2026, 10, 23, 7, 5, tzinfo=UTC), TZ) == "00:05"


class TestQuestService:
    async def test_passes_normalized_preferences_and_address_through(self):
        extractor = AsyncMock()
        extractor.extract_preferences.return_value = {"desiredTime": "abc", "travelMethod": "Biking"}
        locations = AsyncMock()
        locations.find_locations.return_value = [l.model_dump() for l in MOCK_LOCATIONS]
        real = MockRoutePlanner()
        planner = AsyncMock()
        planner.plan_route.side_effect = real.plan_route

        result = await make_service(extractor, locations, planner).create_quest(
            UserRequest(message="surprise me", location=UserLocation(address=ADDRESS))
        )

        extractor.extract_preferences.assert_awaited_once_with("surprise me", ADDRESS)
        assert result.preferences.model_dump() == {"desiredTime": 90, "desiredBudget": 30, "locationPreference": "random", "travelMethod": "bike"}
        locations.find_locations.assert_awaited_once_with(result.preferences, ADDRESS)
        plan = planner.plan_route.await_args.args[0]
        assert (plan.address, plan.start_time, plan.timezone, plan.locations) == (ADDRESS, "10:00", TZ, MOCK_LOCATIONS)
        assert result.route.startLocation.address == ADDRESS == result.route.endLocation.address
        assert result.route.quests and result.route.mock is None

    async def test_omitted_location_uses_default_start_address(self):
        locations = AsyncMock()
        locations.find_locations.return_value = [l.model_dump() for l in MOCK_LOCATIONS]
        result = await make_service(locations=locations).create_quest(UserRequest(message="coffee, walking"))
        assert locations.find_locations.await_args.args[1] == DEFAULT_START_ADDRESS
        assert result.route.startLocation.address == result.route.endLocation.address == DEFAULT_START_ADDRESS

    async def test_one_repair_attempt_then_success(self):
        real = MockRoutePlanner()
        bad = {"quests": [{"location": {"name": "Fake", "address": "Nope"}, "arrivalTime": "10:10", "departureTime": "10:20", "travelDistance": 1}]}
        calls = []

        async def plan(request):
            calls.append(request)
            return bad if len(calls) == 1 else await real.plan_route(request)

        planner = AsyncMock()
        planner.plan_route.side_effect = plan
        result = await make_service(planner=planner).create_quest(REQUEST)
        assert len(calls) == 2
        assert "not one of the provided locations" in calls[1].previous_issues[0]
        assert result.route.quests

    async def test_fails_502_after_repair_also_invalid(self):
        planner = AsyncMock()
        planner.plan_route.return_value = {"nonsense": True}
        with pytest.raises(AppError) as e:
            await make_service(planner=planner).create_quest(REQUEST)
        assert (e.value.status_code, e.value.code, e.value.details["upstream"]) == (502, "UPSTREAM_INVALID_RESPONSE", "cursor")
        assert planner.plan_route.await_count == 2

    async def test_fails_502_when_snowflake_count_wrong(self):
        locations = AsyncMock()
        locations.find_locations.return_value = [l.model_dump() for l in MOCK_LOCATIONS[:4]]
        with pytest.raises(AppError) as e:
            await make_service(locations=locations).create_quest(REQUEST)
        assert e.value.status_code == 502 and e.value.details["upstream"] == "snowflake"
        assert "exactly 10" in e.value.details["issues"][0]

    async def test_empty_route_is_no_feasible_route(self):
        planner = AsyncMock()
        planner.plan_route.return_value = {"quests": []}
        with pytest.raises(AppError) as e:
            await make_service(planner=planner).create_quest(REQUEST)
        assert (e.value.status_code, e.value.code) == (422, "NO_FEASIBLE_ROUTE")
        assert (e.value.details["reason"], e.value.details["proven"]) == ("PLANNER_FOUND_NONE", False)

    async def test_provably_unaffordable_skips_the_planner(self):
        extractor = AsyncMock()
        extractor.extract_preferences.return_value = {"desiredBudget": 0}
        locations = AsyncMock()
        locations.find_locations.return_value = [l.model_dump() | {"estimatedCost": 5} for l in MOCK_LOCATIONS]
        planner = AsyncMock()
        with pytest.raises(AppError) as e:
            await make_service(extractor, locations, planner).create_quest(REQUEST)
        assert (e.value.code, e.value.details["reason"], e.value.details["proven"]) == ("NO_FEASIBLE_ROUTE", "NONE_WITHIN_BUDGET", True)
        planner.plan_route.assert_not_awaited()

    async def test_over_budget_route_gets_repair_then_502(self):
        over = {"quests": [{"location": MOCK_LOCATIONS[9].model_dump(), "arrivalTime": "10:10", "departureTime": "10:30", "travelDistance": 1}]}
        planner = AsyncMock()
        planner.plan_route.return_value = over  # arcade alone is $25, exactly the request budget
        assert (await make_service(planner=planner).create_quest(REQUEST)).route.estimatedCost == 25
        over["quests"].append({"location": MOCK_LOCATIONS[0].model_dump(), "arrivalTime": "10:40", "departureTime": "10:50", "travelDistance": 1})
        with pytest.raises(AppError) as e:
            await make_service(planner=planner).create_quest(REQUEST)
        assert e.value.code == "UPSTREAM_INVALID_RESPONSE"
        assert any("over the $25.00 budget" in i for i in e.value.details["issues"])
        assert "over the $25.00 budget" in planner.plan_route.await_args.args[0].previous_issues[0]

    async def test_labels_mock_responses(self):
        assert (await make_service(mock=True).create_quest(REQUEST)).route.mock is True


class TestHttp:
    def test_health(self):
        res = client().get("/health")
        assert res.status_code == 200 and res.json() == {"status": "ok"}
        assert res.headers["x-content-type-options"] == "nosniff"

    def test_create_quest_without_location(self):
        res = client().post("/v1/quests", json={"message": "I have 2 hours and $25, want coffee, walking"})
        assert res.status_code == 200, res.text
        assert res.json()["startLocation"] == {"address": DEFAULT_START_ADDRESS}

    def test_create_quest_round_trip(self):
        res = client().post("/v1/quests", json=BODY)
        assert res.status_code == 200
        body = res.json()
        assert body["startLocation"] == {"address": ADDRESS} == body["endLocation"]
        assert body["quests"][0] == {"location": MOCK_LOCATIONS[0].model_dump(), "arrivalTime": "10:20", "departureTime": "10:40", "travelDistance": 1}
        assert "mock" not in body
        assert res.headers["x-request-id"]

    @pytest.mark.parametrize(
        ("payload", "path"),
        [
            ({}, "message"),
            ({"message": "hi", "location": {"address": "ab"}}, "location.address"),
            ({"message": "   ", "location": {"address": ADDRESS}}, "message"),
            ({"message": "hi", "location": {"address": "x" * 301}}, "location.address"),
            ({"message": "x" * 2001, "location": {"address": ADDRESS}}, "message"),
        ],
    )
    def test_rejects_invalid_body(self, payload, path):
        res = client().post("/v1/quests", json=payload)
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"
        assert path in [d["path"] for d in res.json()["error"]["details"]]

    def test_malformed_json(self):
        res = client().post("/v1/quests", content="{bad", headers={"content-type": "application/json"})
        assert res.status_code == 400 and res.json()["error"]["message"] == "Malformed JSON body."

    def test_body_too_large(self):
        big = {"message": "x" * 20_000, "location": {"address": ADDRESS}}
        assert client().post("/v1/quests", json=big).status_code == 413

    def test_upstream_outage_maps_to_503_without_internals(self):
        extractor = AsyncMock()
        extractor.extract_preferences.side_effect = upstream_unavailable("cursor")
        res = client(make_service(extractor=extractor)).post("/v1/quests", json=BODY)
        assert res.status_code == 503
        assert res.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"
        assert res.json()["error"]["details"] == {"upstream": "cursor"}

    def test_unexpected_errors_are_generic_500(self):
        extractor = AsyncMock()
        extractor.extract_preferences.side_effect = RuntimeError("db password is hunter2")
        res = client(make_service(extractor=extractor)).post("/v1/quests", json=BODY)
        assert res.status_code == 500 and res.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "hunter2" not in res.text

    def test_rate_limit(self):
        c = client(rate_limit=5)
        codes = [c.post("/v1/quests", json={}).status_code for _ in range(6)]
        assert codes == [400] * 5 + [429]
        assert c.get("/health").status_code == 200  # exempt

    def test_rate_limiter_window_resets(self):
        t = [0.0]
        limiter = FixedWindowRateLimiter(1, clock=lambda: t[0])
        assert limiter.hit("a") is None and limiter.hit("a") is not None
        t[0] = 61
        assert limiter.hit("a") is None

    def test_cors(self):
        c = client()
        allowed = c.get("/health", headers={"origin": "http://localhost:3000"})
        denied = c.get("/health", headers={"origin": "https://evil.example"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "access-control-allow-origin" not in denied.headers

    def test_unknown_route(self):
        res = client().get("/nope")
        assert res.status_code == 404 and res.json()["error"]["code"] == "NOT_FOUND"
