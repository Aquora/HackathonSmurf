import math
import re
from typing import Any

from .types import DEFAULT_PREFERENCES, Preferences

MAX_TIME_MINUTES = 24 * 60
MAX_BUDGET_DOLLARS = 10_000
MAX_TEXT_LENGTH = 200

TRAVEL_SYNONYMS = {
    "drive": "drive", "driving": "drive", "car": "drive",
    "walk": "walk", "walking": "walk", "on foot": "walk", "foot": "walk",
    "bike": "bike", "biking": "bike", "bicycle": "bike", "cycling": "bike",
    "transit": "transit", "public transit": "transit", "public transport": "transit",
    "bus": "transit", "train": "transit", "metro": "transit", "subway": "transit",
}  # fmt: skip

_UNIT_SUFFIX = re.compile(r"\s*(minutes?|mins?|dollars?|usd)\s*$", re.IGNORECASE)


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str) and value.strip():
        # Accept "$25", "90 min", "1,000".
        text = _UNIT_SUFFIX.sub("", value.replace("$", "").replace(",", "")).strip()
        try:
            n = float(text)
        except ValueError:
            return None
        return n if math.isfinite(n) else None
    return None


def _to_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > MAX_TEXT_LENGTH:
        return None
    return text


def normalize_travel_method(value: Any) -> str:
    text = _to_text(value)
    if not text:
        return DEFAULT_PREFERENCES.travelMethod
    text = text.lower()
    return TRAVEL_SYNONYMS.get(text, text)


def normalize_preferences(raw: Any) -> Preferences:
    """Turn untrusted model output into valid Preferences, defaulting any missing or invalid field. Never raises."""
    obj: dict[str, Any] = raw if isinstance(raw, dict) else {}
    time = _to_number(obj.get("desiredTime"))
    budget = _to_number(obj.get("desiredBudget"))
    return Preferences(
        desiredTime=round(time) if time is not None and 0 < time <= MAX_TIME_MINUTES else DEFAULT_PREFERENCES.desiredTime,
        desiredBudget=(
            round(budget, 2) if budget is not None and 0 <= budget <= MAX_BUDGET_DOLLARS else DEFAULT_PREFERENCES.desiredBudget
        ),
        locationPreference=_to_text(obj.get("locationPreference")) or DEFAULT_PREFERENCES.locationPreference,
        travelMethod=normalize_travel_method(obj.get("travelMethod")),
    )
