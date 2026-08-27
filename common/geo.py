"""GeoProvider port (§9). NullGeo/haversine now; OSM and Google adapters
become drop-in replacements selected by settings.GEO_PROVIDER."""
from math import asin, cos, radians, sin, sqrt


def haversine_m(a, b):
    """Great-circle metres between two (lat, lng) tuples."""
    lat1, lng1, lat2, lng2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


class GeoProvider:
    def forward(self, query, near=None):
        return []  # -> [PlaceSuggestion]

    def reverse(self, lat, lng):
        return {}  # -> Place

    def route(self, a, b):
        distance = haversine_m(a, b)
        return {"distance_m": round(distance), "duration_s": round(distance / 7), "polyline": ""}


def provider():
    return GeoProvider()
