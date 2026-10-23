import pytest

from app.domain.normalization import QuestRequest, normalize
from app.errors import ApiError
from tests.fixtures import settings

FULL = {
    "start": {"latitude": 34.05, "longitude": -117.75},
    "departure_time": "2026-10-24T10:00:00-07:00",
    "timezone": "America/Los_Angeles",
}


def run(body: dict, **settings_overrides):
    return normalize(QuestRequest.model_validate(body), settings(**settings_overrides))


def applied_fields(result) -> set[str]:
    return {d.field for d in result.defaults_applied}


def test_omitted_inputs_get_confirmed_defaults():
    result = run(FULL)
    c = result.constraints
    assert c.available_seconds == 5400
    assert (c.budget.amount_minor, c.budget.currency) == (3000, "USD")
    assert c.interests == []
    assert c.return_to_start is False
    assert applied_fields(result) == {"available_seconds", "budget", "interests", "return_to_start"}
    assert result.defaults_version == "defaults_v1"


def test_valid_overrides_are_preserved_and_not_reported_as_defaults():
    body = {
        **FULL,
        "available_seconds": 3600,
        "budget": {"amount_minor": 2000, "currency": "USD"},
        "interests": ["Coffee", " art ", "coffee"],
        "return_to_start": True,
    }
    result = run(body)
    c = result.constraints
    assert c.available_seconds == 3600
    assert c.budget.amount_minor == 2000
    assert c.interests == ["coffee", "art"]
    assert c.return_to_start is True
    assert result.defaults_applied == []


def test_explicit_zero_budget_is_kept():
    result = run({**FULL, "budget": {"amount_minor": 0, "currency": "USD"}})
    assert result.constraints.budget.amount_minor == 0
    assert "budget" not in applied_fields(result)


def test_explicit_empty_interests_is_not_a_default():
    result = run({**FULL, "interests": []})
    assert result.constraints.interests == []
    assert "interests" not in applied_fields(result)


@pytest.mark.parametrize(
    "patch",
    [
        {"available_seconds": None},
        {"available_seconds": 0},
        {"available_seconds": -60},
        {"available_seconds": "5400"},
        {"available_seconds": True},
        {"budget": {"amount_minor": -1, "currency": "USD"}},
        {"budget": {"amount_minor": 2000}},
        {"budget": {"amount_minor": 20.5, "currency": "USD"}},
        {"interests": None},
        {"start": {"latitude": 91, "longitude": 0}},
        {"departure_time": "2026-10-24T10:00:00"},
        {"unexpected": 1},
    ],
)
def test_malformed_values_fail_model_validation(patch):
    with pytest.raises(ValueError):
        QuestRequest.model_validate({**FULL, **patch})


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"budget": {"amount_minor": 2000, "currency": "EUR"}}, "budget.currency"),
        ({"available_seconds": 10**6}, "available_seconds"),
        ({"interests": [""]}, "interests.0"),
        ({"timezone": "Mars/Base"}, "timezone"),
        ({"departure_time": "2026-10-24T10:00:00-05:00"}, "departure_time"),
    ],
)
def test_invalid_supplied_values_are_rejected_not_defaulted(patch, field):
    with pytest.raises(ApiError) as exc:
        run({**FULL, **patch})
    assert exc.value.code == "VALIDATION_ERROR"
    assert field in [e["field"] for e in exc.value.field_errors]


def test_dst_offset_is_checked_against_the_timezone():
    # 2026-11-02 is after the DST change: Los Angeles is -08:00.
    result = run({**FULL, "departure_time": "2026-11-02T10:00:00-08:00"})
    assert result.constraints.departure_time.utcoffset().total_seconds() == -8 * 3600
    with pytest.raises(ApiError):
        run({**FULL, "departure_time": "2026-11-02T10:00:00-07:00"})


def test_missing_currency_config_is_a_configuration_error():
    with pytest.raises(ApiError) as exc:
        run(FULL, default_currency=None)
    assert exc.value.code == "CONFIGURATION_ERROR"


@pytest.mark.parametrize("missing", ["start", "timezone", "departure_time"])
def test_missing_context_without_fallback_fails_explicitly(missing):
    body = {k: v for k, v in FULL.items() if k != missing}
    with pytest.raises(ApiError) as exc:
        run(body)
    assert exc.value.code == "CONFIGURATION_ERROR"


def test_configured_fallbacks_are_disclosed():
    body = {"departure_time": FULL["departure_time"]}
    result = run(
        body,
        neighborhood_anchor_latitude=34.06,
        neighborhood_anchor_longitude=-117.74,
        default_timezone="America/Los_Angeles",
    )
    assert result.constraints.start.latitude == 34.06
    assert {"start", "timezone"} <= applied_fields(result)
