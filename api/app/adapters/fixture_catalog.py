"""Synthetic stand-in for the Snowflake top-10 query. Every place is fake and demo-labeled.

Mirrors the proposed ranking (docs/TEAM-CONTRACT.md §6): drop places with unknown
hours/cost or another currency, then order by interest overlap (desc), straight-line
distance from start (asc), and place_id. Local opening hours are converted to
absolute intervals on the departure date, as the real adapter must do.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from app.adapters.geo import haversine_meters
from app.domain.models import (
    Candidate,
    CandidateSet,
    Constraints,
    Coordinates,
    Fact,
    Money,
    OpeningInterval,
)

RANKING_VERSION = "fixture_ranking_v1"
CATALOG_TZ = "America/Los_Angeles"
VERIFIED_AT = datetime(2026, 10, 20, 19, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Place:
    n: int
    name: str
    tags: tuple[str, ...]
    lat: float
    lon: float
    hours: tuple[str, str] | None  # local "HH:MM" open/close; None = unknown
    cost_minor: int | None  # USD minor units; None = unknown
    visit_seconds: int
    facts: tuple[str, ...]


# fmt: off
_CATALOG = (
    _Place(1, "Demo Bean Coffee", ("coffee", "cafe"), 34.0571, -117.7502, ("07:00", "17:00"), 600,
           1200, ("Roasts a house blend on site.", "Has a chalkboard of local events.")),
    _Place(2, "Demo Corner Gallery", ("art", "gallery"), 34.0583, -117.7489, ("10:00", "17:00"), 0,
           1500, ("Rotates student exhibitions monthly.",)),
    _Place(3, "Demo Mural Alley", ("art", "outdoors"), 34.0566, -117.7471, ("06:00", "22:00"), 0,
           600, ("Features a mural of the old citrus packing houses.",)),
    _Place(4, "Demo Used Books", ("books", "shopping"), 34.0549, -117.7518, ("10:00", "19:00"), 1000,
           1200, ("Keeps a shelf of staff-picked local authors.",)),
    _Place(5, "Demo Taco Stand", ("food", "tacos"), 34.0540, -117.7493, ("11:00", "21:00"), 1200,
           1500, ("Serves a daily special written on the window.",)),
    _Place(6, "Demo Pocket Park", ("outdoors", "park"), 34.0590, -117.7510, ("06:00", "20:00"), 0,
           900, ("Has a little free library by the bench.",)),
    _Place(7, "Demo Tea House", ("coffee", "tea"), 34.0558, -117.7455, ("09:00", "18:00"), 700,
           1200, ("Offers a tasting flight of three teas.",)),
    _Place(8, "Demo Record Shop", ("music", "shopping"), 34.0577, -117.7530, ("11:00", "19:00"), None,
           1200, ("Sorts records by decade.",)),
    _Place(9, "Demo History Museum", ("history", "art"), 34.0601, -117.7480, None, 1500,
           2400, ("Displays a restored 1920s streetcar sign.",)),
)
# fmt: on


def _intervals(place: _Place, departure: datetime) -> list[OpeningInterval] | None:
    if place.hours is None:
        return None
    zone = ZoneInfo(CATALOG_TZ)
    day = departure.astimezone(zone).date()
    opens, closes = (time.fromisoformat(h) for h in place.hours)
    return [
        OpeningInterval(
            opens_at=datetime.combine(day, opens, zone),
            closes_at=datetime.combine(day, closes, zone),
        )
    ]


def _record(place: _Place, constraints: Constraints, rank: int, reasons: list[str]) -> Candidate:
    pid = f"demo_place_{place.n:03d}"
    return Candidate(
        place_id=pid,
        business_id=None,
        name=place.name,
        description="Synthetic demo place for development; not a real business.",
        tags=list(place.tags),
        coordinates=Coordinates(latitude=place.lat, longitude=place.lon),
        timezone=CATALOG_TZ,
        opening_intervals=_intervals(place, constraints.departure_time),
        estimated_cost=None
        if place.cost_minor is None
        else Money(amount_minor=place.cost_minor, currency="USD"),
        visit_seconds=place.visit_seconds,
        facts=[
            Fact(
                fact_id=f"{pid}_fact_{i}",
                text=text,
                source_url=f"https://example.invalid/demo/{pid}",
                verified_at=VERIFIED_AT,
            )
            for i, text in enumerate(place.facts, start=1)
        ],
        source_url=f"https://example.invalid/demo/{pid}",
        verified_at=VERIFIED_AT,
        publication_rights="synthetic",
        demo=True,
        rank=rank,
        match_reasons=reasons,
    )


class FixtureCandidateSource:
    demo = True

    def __init__(self, catalog: tuple[_Place, ...] = _CATALOG) -> None:
        self._catalog = catalog

    def fetch(self, request_id: str, constraints: Constraints, limit: int) -> CandidateSet:
        interests = set(constraints.interests)
        eligible = [
            p
            for p in self._catalog
            if p.hours is not None
            and p.cost_minor is not None
            and constraints.budget.currency == "USD"
        ]

        def sort_key(p: _Place):
            overlap = len(interests & set(p.tags))
            distance = haversine_meters(
                constraints.start, Coordinates(latitude=p.lat, longitude=p.lon)
            )
            return (-overlap, distance, p.n)

        ranked = sorted(eligible, key=sort_key)[:limit]
        candidates = []
        for rank, p in enumerate(ranked, start=1):
            matched = sorted(interests & set(p.tags))
            reasons = [f"tag: {t}" for t in matched] or ["ranked by distance from start"]
            candidates.append(_record(p, constraints, rank, reasons))
        return CandidateSet(
            request_id=request_id,
            retrieved_at=datetime.now(UTC),
            ranking_version=RANKING_VERSION,
            constraints=constraints,
            candidates=candidates,
            candidate_count=len(candidates),
        )
