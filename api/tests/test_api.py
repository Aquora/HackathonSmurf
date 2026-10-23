import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fixtures import settings

BODY = {
    "start": {"latitude": 34.05, "longitude": -117.75},
    "departure_time": "2026-10-24T10:00:00-07:00",
    "timezone": "America/Los_Angeles",
}


@pytest.fixture
def client():
    return TestClient(create_app(settings()), raise_server_exceptions=False)


def assert_envelope(resp, status, code):
    assert resp.status_code == status
    error = resp.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == resp.headers["x-request-id"]
    assert isinstance(error["details"]["field_errors"], list)
    assert isinstance(error["details"]["suggested_adjustments"], list)
    return error


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers["x-request-id"].startswith("req_")


def test_validation_errors_use_the_shared_envelope(client):
    resp = client.post("/v1/quests", json={**BODY, "available_seconds": -1})
    error = assert_envelope(resp, 422, "VALIDATION_ERROR")
    assert any(e["field"] == "available_seconds" for e in error["details"]["field_errors"])
    assert "constraints" not in error["details"]


def test_malformed_json_uses_the_shared_envelope(client):
    resp = client.post(
        "/v1/quests", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert_envelope(resp, 422, "VALIDATION_ERROR")


def test_explicit_null_is_rejected(client):
    resp = client.post("/v1/quests", json={**BODY, "budget": None})
    assert_envelope(resp, 422, "VALIDATION_ERROR")


def test_fixture_quest_matches_contract_shape(client):
    resp = client.post("/v1/quests", json={**BODY, "interests": ["coffee", "art"]})
    assert resp.status_code == 201, resp.text
    quest = resp.json()

    assert quest["quest_id"].startswith("quest_")
    assert quest["constraints"]["budget"] == {"amount_minor": 3000, "currency": "USD"}
    assert {d["field"] for d in quest["defaults_applied"]} >= {"available_seconds", "budget"}
    assert quest["defaults_version"] == "defaults_v1"
    assert quest["mode"] == {
        "demo": True,
        "simulation": True,
        "fallback_used": True,
        "routing_source": "fixture",
    }

    stops = quest["stops"]
    assert len(stops) == 3
    assert len({s["place_id"] for s in stops}) == 3
    assert all(s["completion"] == {"status": "pending", "completed_at": None} for s in stops)
    for stop in stops:
        own_facts = {f["fact_id"] for f in stop["facts"]}
        assert stop["challenge"]["fact_ids"] and set(stop["challenge"]["fact_ids"]) <= own_facts

    route = quest["route"]
    assert route["total_seconds"] == route["walking_seconds"] + route["visit_seconds"]
    assert route["walking_seconds"] == sum(leg["walking_seconds"] for leg in route["legs"])
    assert route["visit_seconds"] == sum(s["visit_seconds"] for s in stops)
    assert route["total_seconds"] <= quest["constraints"]["available_seconds"]
    assert quest["estimated_cost"]["amount_minor"] == sum(
        s["estimated_cost"]["amount_minor"] for s in stops
    )
    assert quest["estimated_cost"]["amount_minor"] <= 3000

    legs = route["legs"]
    assert legs[0]["from"] == {"kind": "start", "stop_id": None}
    assert [leg["to"]["stop_id"] for leg in legs] == [s["stop_id"] for s in stops]
    lon, lat = legs[0]["geometry"]["coordinates"][0]
    assert (lat, lon) == (34.05, -117.75)


def test_impossible_time_returns_no_feasible_route_with_context(client):
    resp = client.post("/v1/quests", json={**BODY, "available_seconds": 240})
    error = assert_envelope(resp, 422, "NO_FEASIBLE_ROUTE")
    details = error["details"]
    assert details["reason"] == "TIME_BELOW_MINIMUM"
    assert details["search_scope"] == "retrieved_candidates"
    assert details["constraints"]["available_seconds"] == 240
    assert details["suggested_adjustments"][0]["field"] == "available_seconds"


def test_unsupported_catalog_currency_yields_insufficient_candidates():
    client = TestClient(create_app(settings(default_currency="CAD")))
    error = assert_envelope(client.post("/v1/quests", json=BODY), 422, "NO_FEASIBLE_ROUTE")
    assert error["details"]["reason"] == "INSUFFICIENT_CANDIDATES"


def test_client_request_id_is_echoed_when_safe(client):
    resp = client.get("/health", headers={"x-request-id": "demo_request_001"})
    assert resp.headers["x-request-id"] == "demo_request_001"
    resp = client.get("/health", headers={"x-request-id": "bad id\nwith newline"})
    assert resp.headers["x-request-id"].startswith("req_")


def test_unknown_route_uses_the_envelope(client):
    assert_envelope(client.get("/nope"), 404, "NOT_FOUND")


def test_unexpected_errors_are_safe(client):
    app = client.app

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    resp = client.get("/boom")
    error = assert_envelope(resp, 500, "INTERNAL_ERROR")
    assert "secret" not in resp.text
    assert error["message"] == "An unexpected error occurred."
