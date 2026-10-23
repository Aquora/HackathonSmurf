"""Filter by opening hours, score, and assemble the CandidateSet."""

from datetime import date, datetime, timezone

from . import settings
from .hours import expand_intervals, longest_open_seconds


def search_radius_m(available_seconds):
    """Straight-line search radius; never evidence of walking feasibility."""
    return min(settings.MAX_RADIUS_M, settings.WALKING_SPEED_MPS * available_seconds / 2)


def build_candidate_set(request, rows, weekly_by_place, retrieved_at):
    """``rows`` are nearby places (lower-case keys) with their best preference match."""
    radius = search_radius_m(request.available_seconds)
    scored = []
    for row in rows:
        candidate = _evaluate(row, request, radius, weekly_by_place.get(row["place_id"]))
        if candidate is not None:
            scored.append(candidate)

    scored.sort(key=lambda item: (-item[0], item[1]["distance_m"], item[1]["place_id"]))
    candidates = []
    for rank, (_, candidate) in enumerate(scored[:request.limit], start=1):
        candidate["rank"] = rank
        candidates.append(candidate)

    return {
        "request_id": request.request_id,
        "retrieved_at": retrieved_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ranking_version": settings.RANKING_VERSION,
        "constraints": request.constraints,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _evaluate(row, request, radius, weekly):
    if not weekly:
        return None  # unknown hours are never guessed
    intervals = expand_intervals(weekly, request.timezone, request.window_start, request.window_end)
    if longest_open_seconds(intervals, request.window_start, request.window_end) < settings.MIN_OPEN_SECONDS:
        return None

    dist_m = float(row["dist_m"])
    sim = float(row["sim"]) if row.get("sim") is not None and request.interests else 0.0
    closeness = max(0.0, 1.0 - dist_m / radius) if radius > 0 else 0.0
    score = round(settings.W_SIM * sim + settings.W_DIST * closeness, 6)
    tags = list(row.get("tags") or [])

    return score, {
        "rank": None,
        "place_id": row["place_id"],
        "name": row["name"],
        "tags": tags,
        "coordinates": {"latitude": float(row["latitude"]), "longitude": float(row["longitude"])},
        "distance_m": int(round(dist_m)),
        "address": row.get("address"),
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
