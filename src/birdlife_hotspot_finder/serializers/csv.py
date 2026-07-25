"""CSV serializer for FinderResult."""

import csv
import io
from collections.abc import Callable
from typing import Any

from birdlife_hotspot_finder.models.result import FinderResult

# Type alias for column extractor function
ColumnExtractor = Callable[[dict[str, Any], dict[str, Any]], Any]

# CSV columns - flattened from Location entities with coverage extensions
CSV_COLUMNS: list[tuple[str, ColumnExtractor]] = [
    ("locationID", lambda loc, meta: loc.get("locationID")),
    ("name", lambda loc, meta: loc.get("name")),
    ("latitude", lambda loc, meta: loc.get("decimalLatitude")),
    ("longitude", lambda loc, meta: loc.get("decimalLongitude")),
    (
        "gapType",
        lambda loc, meta: (loc.get("extensions") or {}).get("coverage.gapType", ""),
    ),
    (
        "priorityScore",
        lambda loc, meta: (loc.get("extensions") or {}).get(
            "coverage.priorityScore", ""
        ),
    ),
    (
        "checklistCount",
        lambda loc, meta: (loc.get("extensions") or {}).get(
            "coverage.checklistCount", ""
        ),
    ),
    (
        "reasoning",
        lambda loc, meta: (loc.get("extensions") or {}).get("coverage.reasoning", ""),
    ),
    (
        "nearestHotspot",
        lambda loc, meta: (loc.get("extensions") or {}).get(
            "coverage.nearestHotspotName", ""
        ),
    ),
    (
        "nearestHotspotKm",
        lambda loc, meta: (loc.get("extensions") or {}).get(
            "coverage.nearestHotspotDistanceKm", ""
        ),
    ),
    ("gridSizeKm", lambda loc, meta: meta.get("gridSizeKm")),
    ("region", lambda loc, meta: meta.get("region", "")),
    ("queryTimestamp", lambda loc, meta: meta.get("queryTimestamp", "")),
]


class CsvSerializer:
    """Serialize FinderResult to CSV for spreadsheet tools."""

    def serialize(self, result: FinderResult) -> str:
        """Serialize coverage gaps to CSV string."""
        data = result.to_response_dict()
        meta = data.get("meta", {})

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([col[0] for col in CSV_COLUMNS])

        # Data rows
        for location in data.get("data", []):
            row = [col[1](location, meta) or "" for col in CSV_COLUMNS]
            writer.writerow(row)

        return output.getvalue()
