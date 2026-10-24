"""Filter by opening hours, score, and assemble the result for the API.

The API reads ``locations`` and requires exactly 10 unique items, each with
``name``, ``address``, and ``closingTime`` ("HH:MM"); extra fields are ignored.
"""

from datetime import date, datetime, timezone

from . import settings
from .hours import expand_intervals, longest_open_seconds


def search_radius_m(available_seconds, travel_method):
    """Straight-line search radius; never evidence of travel feasibility."""
    speed, cap = settings.TRAVEL[travel_method]
    return min(cap, speed * available_seconds / 2)


def build_locations(request, rows, weekly_by_place, retrieved_at):
    """``rows`` are open-hours-known places within FILL_RADIUS_M with their best match.

    Places inside the travel radius come first, by score. If they are fewer than
    the limit, the rest are filled with farther open places, by score then distance.
    """
    radius = search_radius_m(request.available_seconds, request.travel_method)
    inside, outside = [], []
    for row in rows:
        scored = _evaluate(row, request, radius, weekly_by_place.get(row["place_id"]))
        if scored is not None:
            (inside if scored[1]["distance_m"] <= radius else outside).append(scored)

    key = lambda item: (-item[0], item[1]["distance_m"], item[1]["place_id"])  # noqa: E731
    chosen = sorted(inside, key=key)[:request.limit]
    fill = sorted(outside, key=key)[:request.limit - len(chosen)]
    for _, location in fill:
        location["within_radius"] = False
        location["match_reasons"].append(
            f"beyond the usual {request.travel_method} range (~{int(radius)} m); added to reach "
            f"{request.limit} open places")

    locations = []
    for rank, (_, location) in enumerate(chosen + fill, start=1):
        location["rank"] = rank
        locations.append(location)

    return {
        "request_id": request.request_id,
        "retrieved_at": retrieved_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ranking_version": settings.RANKING_VERSION,
        "constraints": request.constraints,
        "location_count": len(locations),
        "locations": locations,
    }


def _evaluate(row, request, radius, weekly):
    if not weekly:
        return None  # unknown hours are never guessed
    intervals = expand_intervals(weekly, request.timezone, request.window_start, request.window_end)
    if longest_open_seconds(intervals, request.window_start, request.window_end) < settings.MIN_OPEN_SECONDS:
        return None

    # The interval the user can actually use: the longest open stretch inside the window.
    _, closes_at = max(intervals, key=lambda iv: longest_open_seconds(
        [iv], request.window_start, request.window_end))
    dist_m = float(row["dist_m"])
    row = _demote_drink_only_food_match(row)
    sim = float(row["sim"]) if row.get("sim") is not None and request.interests else 0.0
    closeness = max(0.0, 1.0 - dist_m / radius) if radius > 0 else 0.0
    score = round(settings.W_SIM * sim + settings.W_DIST * closeness, 6)
    tags = list(row.get("tags") or [])

    latitude, longitude = float(row["latitude"]), float(row["longitude"])

    return score, {
        "rank": None,
        "name": row["name"],
        # OSM has no street address for some places; coordinates are a real, usable location.
        "address": row.get("address") or f"{latitude:.6f}, {longitude:.6f}",
        "closingTime": closes_at.strftime("%H:%M"),
        # OSM has no prices: a labeled category estimate (APP.CATEGORY_COST), or None.
        "estimatedCost": None if row.get("cost_usd") is None else round(float(row["cost_usd"]), 2),
        "costBasis": (None if row.get("cost_usd") is None else
                      f"category estimate: typical spend at a '{row['cost_label']}', "
                      f"not this place's actual price"),
        "place_id": row["place_id"],
        "tags": tags,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "distance_m": int(round(dist_m)),
        "within_radius": True,
        "website": row.get("website"),
        "opening_intervals": [
            {"opens_at": o.isoformat(timespec="seconds"), "closes_at": c.isoformat(timespec="seconds")}
            for o, c in intervals
        ],
        "hours_as_of": _iso_date(row.get("snapshot_date")),
        "source_url": f"https://www.openstreetmap.org/{row['osm_ref']}",
        "attribution": settings.ATTRIBUTION,
        "match_reasons": match_reasons(row, request, tags, dist_m),
    }


def _demote_drink_only_food_match(row):
    """A juice bar or boba shop is not a "food" match just because OSM calls it fast food."""
    interest = (row.get("sim_interest") or "").lower()
    if row.get("sim") is None or interest not in settings.FOOD_INTERESTS:
        return row
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    cuisines = tags - settings.GENERIC_FOOD_TAGS
    if not (cuisines & settings.DRINK_ONLY_TAGS) or (cuisines - settings.DRINK_ONLY_TAGS):
        return row  # no drink-only cuisine, or it also has a food cuisine (e.g. juice + sandwich)
    return {**row, "sim": float(row["sim"]) * settings.DRINK_ONLY_FOOD_FACTOR}


def match_reasons(row, request, tags, dist_m):
    """Reasons built only from tags, the measured match, and distance."""
    reasons = []
    exact = set()
    for interest in request.interests:
        for tag in tags:
            if tag.lower() == interest:
                reasons.append(f"tag '{tag}' matches interest '{interest}'")
                exact.add(interest)
                break

    sim, label, interest = row.get("sim"), row.get("sim_label"), row.get("sim_interest")
    if (request.interests and sim is not None and label and interest
            and float(sim) >= settings.REASON_THRESHOLD and interest not in exact):
        if row.get("sim_kind") == "semantic":
            reasons.append(f"tag '{label}' is the closest category to "
                           f"'{interest}' (Cortex embedding)")
        else:
            reasons.append(f"tag '{label}' related to interest '{interest}'")

    reasons.append(f"~{int(round(dist_m / 10.0) * 10)} m straight-line from start")
    return reasons


def _iso_date(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
