import math

from app.domain.models import Coordinates

EARTH_RADIUS_M = 6_371_000


def haversine_meters(a: Coordinates, b: Coordinates) -> int:
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(2 * EARTH_RADIUS_M * math.asin(math.sqrt(h)))
