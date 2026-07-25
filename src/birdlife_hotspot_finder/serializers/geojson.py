"""GeoJSON serializer for FinderResult.

Produces GeoJSON FeatureCollection for mapping tools (Leaflet, QGIS, etc.).
"""

import json
from typing import Any

from birdlife_hotspot_finder.models.result import FinderResult


class GeoJsonSerializer:
    """Serialize FinderResult to GeoJSON FeatureCollection."""

    def __init__(self, indent: int | None = 2) -> None:
        self.indent = indent

    def serialize(self, result: FinderResult) -> str:
        """Serialize coverage gaps to GeoJSON string.

        Each gap becomes a Point feature with coverage extensions as properties.
        """
        data = result.to_response_dict()
        meta = data.get("meta", {})

        features: list[dict[str, Any]] = []

        for location in data.get("data", []):
            lat = location.get("decimalLatitude")
            lng = location.get("decimalLongitude")

            if lat is None or lng is None:
                continue

            # Extract extensions and flatten for properties
            extensions = location.get("extensions", {})
            properties: dict[str, Any] = {
                "locationID": location.get("locationID"),
                "name": location.get("name"),
                "slug": location.get("slug"),
                # Flatten coverage extensions (remove namespace prefix)
                "gapType": extensions.get("coverage.gapType"),
                "priorityScore": self._parse_float(
                    extensions.get("coverage.priorityScore")
                ),
                "checklistCount": self._parse_int(
                    extensions.get("coverage.checklistCount")
                ),
                "reasoning": extensions.get("coverage.reasoning"),
                "nearestHotspotName": extensions.get("coverage.nearestHotspotName"),
                "nearestHotspotDistanceKm": self._parse_float(
                    extensions.get("coverage.nearestHotspotDistanceKm")
                ),
                # Meta info
                "gridSizeKm": meta.get("gridSizeKm"),
                "region": meta.get("region"),
            }

            # Remove None values for cleaner output
            properties = {k: v for k, v in properties.items() if v is not None}

            feature: dict[str, Any] = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat],  # GeoJSON is [lng, lat]
                },
                "properties": properties,
            }
            features.append(feature)

        geojson: dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "resultType": meta.get("resultType"),
                "queryTimestamp": meta.get("queryTimestamp"),
                "gridSizeKm": meta.get("gridSizeKm"),
                "totalGaps": len(features),
            },
        }

        return json.dumps(geojson, indent=self.indent)

    def _parse_float(self, value: str | None) -> float | None:
        """Parse string to float, return None if invalid."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value: str | None) -> int | None:
        """Parse string to int, return None if invalid."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
