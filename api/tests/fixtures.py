"""Synthetic, demo-labeled test data. Not real places; IDs are fixture-only."""

from datetime import datetime, timedelta

from app.config import Settings
from app.domain.models import (
    Candidate,
    CandidateSet,
    Challenge,
    Constraints,
    Coordinates,
    Fact,
    LegEndpoint,
    Money,
    OpeningInterval,
    ProposedStop,
    QuestProposal,
    WalkingLeg,
)

TZ = "America/Los_Angeles"
DEPARTURE = datetime.fromisoformat("2026-10-24T10:00:00-07:00")
VERIFIED = datetime.fromisoformat("2026-10-20T12:00:00-07:00")


def settings(**overrides) -> Settings:
    base = {
        "default_currency": "USD",
        "default_timezone": None,
        "neighborhood_anchor_latitude": None,
        "neighborhood_anchor_longitude": None,
    }
    return Settings(_env_file=None, **{**base, **overrides})


def constraints(**overrides) -> Constraints:
    base = {
        "start": Coordinates(latitude=34.05, longitude=-117.75),
        "departure_time": DEPARTURE,
        "timezone": TZ,
        "available_seconds": 5400,
        "budget": Money(amount_minor=3000, currency="USD"),
        "interests": ["coffee", "art"],
        "return_to_start": False,
    }
    return Constraints(**{**base, **overrides})


def candidate(n: int, **overrides) -> Candidate:
    pid = f"demo_place_{n:03d}"
    base = {
        "place_id": pid,
        "business_id": None,
        "name": f"Demo Place {n}",
        "description": "Synthetic test place.",
        "tags": ["coffee"],
        "coordinates": Coordinates(latitude=34.05 + n / 1000, longitude=-117.75),
        "timezone": TZ,
        "opening_intervals": [
            OpeningInterval(
                opens_at=DEPARTURE - timedelta(hours=2), closes_at=DEPARTURE + timedelta(hours=8)
            )
        ],
        "estimated_cost": Money(amount_minor=800, currency="USD"),
        "visit_seconds": 1200,
        "facts": [
            Fact(
                fact_id=f"{pid}_fact_1",
                text="Synthetic fact.",
                source_url="https://example.invalid/demo",
                verified_at=VERIFIED,
            )
        ],
        "source_url": "https://example.invalid/demo",
        "verified_at": VERIFIED,
        "publication_rights": "synthetic",
        "demo": True,
        "rank": n,
        "match_reasons": ["tag: coffee"],
    }
    return Candidate(**{**base, **overrides})


def candidate_set(candidates: list[Candidate], c: Constraints | None = None) -> CandidateSet:
    return CandidateSet(
        request_id="demo_request_001",
        retrieved_at=DEPARTURE - timedelta(minutes=1),
        ranking_version="demo_ranking_v1",
        constraints=c or constraints(),
        candidates=candidates,
        candidate_count=len(candidates),
    )


def proposal(place_ids: list[str], fact_ids: dict[str, list[str]] | None = None) -> QuestProposal:
    fact_ids = fact_ids or {}
    return QuestProposal(
        title="Demo quest",
        ordered_stops=[
            ProposedStop(
                place_id=pid,
                why_selected="Matches interests.",
                challenge=Challenge(
                    text="Find the thing.", fact_ids=fact_ids.get(pid, [f"{pid}_fact_1"])
                ),
            )
            for pid in place_ids
        ],
        planning_rationale="Short walk.",
    )


def legs(
    place_ids: list[str], walking_seconds: int = 300, return_to_start: bool = False
) -> list[WalkingLeg]:
    points = [LegEndpoint(kind="start")] + [LegEndpoint(kind="stop", place_id=p) for p in place_ids]
    if return_to_start:
        points.append(LegEndpoint(kind="start"))
    return [
        WalkingLeg(
            from_=a,
            to=b,
            walking_seconds=walking_seconds,
            distance_meters=400,
            geometry={"type": "LineString", "coordinates": [[-117.75, 34.05], [-117.75, 34.051]]},
        )
        for a, b in zip(points, points[1:], strict=False)
    ]
