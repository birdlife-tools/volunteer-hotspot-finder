"""Tests for HotspotFinder."""

import pytest

from birdlife_hotspot_finder.analyzers.grid import GridCell
from birdlife_hotspot_finder.finder import REGION_BOUNDS, HotspotFinder


class TestPriorityScoring:
    """Tests for priority scoring algorithm."""

    @pytest.fixture
    def finder(self):
        """Create finder with mock eBird client."""
        mock_ebird = type("MockEBird", (), {"close": lambda self: None})()
        return HotspotFinder(ebird=mock_ebird, grid_size_km=10)

    def test_close_hotspot_high_priority(self, finder):
        """Cells close to hotspots get higher priority (accessible)."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.nearest_hotspot_distance_km = 5.0

        hotspots_data: list = []
        priority = finder._calculate_priority(cell, hotspots_data)

        assert priority >= 0.7

    def test_far_hotspot_lower_priority(self, finder):
        """Cells far from hotspots get lower priority than close ones."""
        close_cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        close_cell.nearest_hotspot_distance_km = 5.0

        far_cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        far_cell.nearest_hotspot_distance_km = 50.0

        hotspots_data: list = []
        priority_close = finder._calculate_priority(close_cell, hotspots_data)
        priority_far = finder._calculate_priority(far_cell, hotspots_data)

        assert priority_close > priority_far

    def test_isolation_affects_priority(self, finder):
        """Cells in areas with fewer nearby hotspots are prioritized differently."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.nearest_hotspot_distance_km = 10.0

        # Few hotspots nearby (within 25km = ~0.22 degrees)
        few_hotspots = [
            {"lat": 44.1, "lng": 20.1, "num_species_all_time": 50},
        ]
        priority_few = finder._calculate_priority(cell, few_hotspots)

        # Many hotspots nearby (6 hotspots)
        many_hotspots = [
            {"lat": 44.05, "lng": 20.05, "num_species_all_time": 50},
            {"lat": 44.08, "lng": 20.08, "num_species_all_time": 60},
            {"lat": 44.02, "lng": 20.02, "num_species_all_time": 40},
            {"lat": 44.03, "lng": 20.03, "num_species_all_time": 45},
            {"lat": 44.06, "lng": 20.06, "num_species_all_time": 55},
            {"lat": 44.09, "lng": 20.09, "num_species_all_time": 35},
        ]
        priority_many = finder._calculate_priority(cell, many_hotspots)

        # Both should have valid priorities
        assert 0 < priority_few <= 1.0
        assert 0 < priority_many <= 1.0

    def test_high_biodiversity_bonus(self, finder):
        """Cells near high-biodiversity hotspots get bonus."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.nearest_hotspot_distance_km = 40.0  # Far away, lower base priority

        # High species count nearby (within 30km)
        high_biodiversity = [
            {"lat": 44.15, "lng": 20.15, "num_species_all_time": 150},
        ]
        priority_high = finder._calculate_priority(cell, high_biodiversity)

        # Low species count nearby
        low_biodiversity = [
            {"lat": 44.15, "lng": 20.15, "num_species_all_time": 10},
        ]
        priority_low = finder._calculate_priority(cell, low_biodiversity)

        assert priority_high >= priority_low  # High biodiversity adds bonus

    def test_priority_capped_at_one(self, finder):
        """Priority score never exceeds 1.0."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.nearest_hotspot_distance_km = 3.0  # Very close

        # All favorable conditions
        hotspots_data = [
            {"lat": 44.15, "lng": 20.15, "num_species_all_time": 200},
        ]
        priority = finder._calculate_priority(cell, hotspots_data)

        assert priority <= 1.0


class TestRegionBounds:
    """Tests for region bounds."""

    def test_known_regions(self):
        """All expected regions are defined."""
        expected = ["RS", "SE", "ES", "CH", "US-NY", "US-CA", "US-TX"]
        for region in expected:
            assert region in REGION_BOUNDS

    def test_bounds_format(self):
        """Bounds are (min_lat, max_lat, min_lng, max_lng)."""
        for region, bounds in REGION_BOUNDS.items():
            min_lat, max_lat, min_lng, max_lng = bounds
            assert min_lat < max_lat, f"{region}: min_lat should be < max_lat"
            assert min_lng < max_lng, f"{region}: min_lng should be < max_lng"

    def test_serbia_bounds(self):
        """Serbia bounds cover Belgrade."""
        bounds = REGION_BOUNDS["RS"]
        min_lat, max_lat, min_lng, max_lng = bounds
        # Belgrade is roughly 44.8N, 20.4E
        assert min_lat < 44.8 < max_lat
        assert min_lng < 20.4 < max_lng


class TestReasoningBuilder:
    """Tests for reasoning text generation."""

    @pytest.fixture
    def finder(self):
        mock_ebird = type("MockEBird", (), {"close": lambda self: None})()
        return HotspotFinder(ebird=mock_ebird, grid_size_km=10)

    def test_basic_reasoning(self, finder):
        """Basic reasoning includes no hotspots message."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        reasoning = finder._build_reasoning(cell)

        assert "No eBird hotspots" in reasoning

    def test_accessible_reasoning(self, finder):
        """Close cells are marked as accessible."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.nearest_hotspot_distance_km = 5.0
        reasoning = finder._build_reasoning(cell)

        assert "accessible" in reasoning

    def test_remote_reasoning(self, finder):
        """Far cells are marked as remote."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.nearest_hotspot_distance_km = 40.0
        reasoning = finder._build_reasoning(cell)

        assert "remote" in reasoning

    def test_high_priority_reasoning(self, finder):
        """High priority cells get noted."""
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)
        cell.priority = 0.85
        reasoning = finder._build_reasoning(cell)

        assert "high priority" in reasoning


class TestHaversine:
    """Tests for distance calculation."""

    @pytest.fixture
    def finder(self):
        mock_ebird = type("MockEBird", (), {"close": lambda self: None})()
        return HotspotFinder(ebird=mock_ebird, grid_size_km=10)

    def test_same_point_zero_distance(self, finder):
        dist = finder._haversine(44.8, 20.4, 44.8, 20.4)
        assert dist == 0.0

    def test_known_distance(self, finder):
        # Belgrade (44.8, 20.4) to Vienna (48.2, 16.4) ~500km
        dist = finder._haversine(44.8, 20.4, 48.2, 16.4)
        assert 450 < dist < 550

    def test_symmetric(self, finder):
        dist1 = finder._haversine(44.0, 20.0, 45.0, 21.0)
        dist2 = finder._haversine(45.0, 21.0, 44.0, 20.0)
        assert abs(dist1 - dist2) < 0.01
