"""Grid-based coverage analyzer."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..clients.ebird import Hotspot


@dataclass
class GridCell:
    """A grid cell with coverage metrics."""

    lat: float
    lng: float
    grid_size_km: int
    hotspot_count: int = 0
    checklist_count: int = 0
    nearest_hotspot: Hotspot | None = None
    nearest_hotspot_distance_km: float | None = None
    priority: float = 0.5

    @property
    def has_coverage(self) -> bool:
        """Cell has at least one hotspot."""
        return self.hotspot_count > 0


class GridAnalyzer:
    """Analyze coverage using a grid overlay."""

    def __init__(self, grid_size_km: int = 10) -> None:
        self.grid_size_km = grid_size_km

    def _km_to_deg_lat(self, km: float) -> float:
        """Convert km to degrees latitude (approximately constant)."""
        return km / 111.0

    def _km_to_deg_lng(self, km: float, lat: float) -> float:
        """Convert km to degrees longitude (varies with latitude)."""
        return km / (111.0 * math.cos(math.radians(lat)))

    def _haversine_km(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Calculate distance between two points in km."""
        r = 6371  # Earth radius in km
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def create_grid(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
    ) -> list[GridCell]:
        """Create a grid of cells covering a bounding box.

        Args:
            min_lat, max_lat: Latitude bounds
            min_lng, max_lng: Longitude bounds

        Returns:
            List of GridCell objects centered at each cell
        """
        cells: list[GridCell] = []

        # Calculate step sizes
        lat_step = self._km_to_deg_lat(self.grid_size_km)
        center_lat = (min_lat + max_lat) / 2
        lng_step = self._km_to_deg_lng(self.grid_size_km, center_lat)

        lat = min_lat + lat_step / 2
        while lat < max_lat:
            lng = min_lng + lng_step / 2
            while lng < max_lng:
                cells.append(
                    GridCell(
                        lat=round(lat, 4),
                        lng=round(lng, 4),
                        grid_size_km=self.grid_size_km,
                    )
                )
                lng += lng_step
            lat += lat_step

        return cells

    def assign_hotspots_to_grid(
        self,
        cells: list[GridCell],
        hotspots: list[Hotspot],
    ) -> list[GridCell]:
        """Assign hotspots to their nearest grid cells and calculate coverage.

        Args:
            cells: Grid cells to populate
            hotspots: Hotspots to assign

        Returns:
            Updated grid cells with hotspot counts
        """
        # Build a simple index for faster lookup
        half_lat = self._km_to_deg_lat(self.grid_size_km) / 2
        center_lat = sum(c.lat for c in cells) / len(cells) if cells else 0
        half_lng = self._km_to_deg_lng(self.grid_size_km, center_lat) / 2

        for hotspot in hotspots:
            for cell in cells:
                # Check if hotspot falls within cell bounds
                if (
                    abs(hotspot.lat - cell.lat) <= half_lat
                    and abs(hotspot.lng - cell.lng) <= half_lng
                ):
                    cell.hotspot_count += 1
                    break

        return cells

    def find_nearest_hotspot(
        self,
        cell: GridCell,
        hotspots: list[Hotspot],
    ) -> tuple[Hotspot | None, float | None]:
        """Find the nearest hotspot to a grid cell.

        Args:
            cell: Grid cell to check
            hotspots: List of hotspots to search

        Returns:
            Tuple of (nearest_hotspot, distance_km)
        """
        if not hotspots:
            return None, None

        nearest: Hotspot | None = None
        min_dist: float = float("inf")

        for hotspot in hotspots:
            dist = self._haversine_km(cell.lat, cell.lng, hotspot.lat, hotspot.lng)
            if dist < min_dist:
                min_dist = dist
                nearest = hotspot

        return nearest, round(min_dist, 2) if nearest else None

    def identify_gaps(
        self,
        cells: list[GridCell],
        hotspots: list[Hotspot],
        min_hotspots: int = 1,
    ) -> list[GridCell]:
        """Identify cells with coverage gaps.

        Args:
            cells: Grid cells to analyze
            hotspots: All hotspots in region (for nearest calculation)
            min_hotspots: Minimum hotspots to consider covered

        Returns:
            List of gap cells (sorted by distance to nearest hotspot)
        """
        gaps: list[GridCell] = []

        for cell in cells:
            if cell.hotspot_count < min_hotspots:
                nearest, dist = self.find_nearest_hotspot(cell, hotspots)
                cell.nearest_hotspot = nearest
                cell.nearest_hotspot_distance_km = dist
                gaps.append(cell)

        # Sort by distance to nearest hotspot (closest gaps first)
        gaps.sort(key=lambda c: c.nearest_hotspot_distance_km or float("inf"))
        return gaps
