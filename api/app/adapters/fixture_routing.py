"""Straight-line walking estimate. Labeled routing_source="fixture"; never a measured route."""

from app.adapters.geo import haversine_meters
from app.domain.models import Coordinates, LegEndpoint, WalkingLeg

WALKING_METERS_PER_SECOND = 1.3
DETOUR_FACTOR = 1.3  # street grids are longer than straight lines


class StraightLineRouter:
    source = "fixture"

    def walking_legs(
        self, start: Coordinates, stops: list[tuple[str, Coordinates]], return_to_start: bool
    ) -> list[WalkingLeg]:
        points = [(LegEndpoint(kind="start"), start)] + [
            (LegEndpoint(kind="stop", place_id=pid), coords) for pid, coords in stops
        ]
        if return_to_start:
            points.append((LegEndpoint(kind="start"), start))

        legs = []
        for (a, a_xy), (b, b_xy) in zip(points, points[1:], strict=False):
            meters = round(haversine_meters(a_xy, b_xy) * DETOUR_FACTOR)
            legs.append(
                WalkingLeg(
                    from_=a,
                    to=b,
                    walking_seconds=round(meters / WALKING_METERS_PER_SECOND),
                    distance_meters=meters,
                    geometry={
                        "type": "LineString",
                        "coordinates": [
                            [a_xy.longitude, a_xy.latitude],
                            [b_xy.longitude, b_xy.latitude],
                        ],
                    },
                )
            )
        return legs
