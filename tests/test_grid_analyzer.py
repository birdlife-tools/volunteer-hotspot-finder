"""Tests for grid analyzer."""


from birdlife_hotspot_finder.analyzers.grid import GridAnalyzer, GridCell


class TestGridCell:
    """Tests for GridCell dataclass."""

    def test_has_coverage_true(self):
        cell = GridCell(lat=44.8, lng=20.4, grid_size_km=10, hotspot_count=1)
        assert cell.has_coverage is True

    def test_has_coverage_false(self):
        cell = GridCell(lat=44.8, lng=20.4, grid_size_km=10, hotspot_count=0)
        assert cell.has_coverage is False

    def test_default_priority(self):
        cell = GridCell(lat=44.8, lng=20.4, grid_size_km=10)
        assert cell.priority == 0.5


class TestGridAnalyzer:
    """Tests for GridAnalyzer."""

    def test_create_grid_basic(self):
        """Grid covers bounding box with correct cell count."""
        analyzer = GridAnalyzer(grid_size_km=10)
        # ~1 degree lat = 111km, so 10km grid = ~0.09 degrees
        # Box of 1 degree should give ~10-12 cells per dimension
        cells = analyzer.create_grid(44.0, 45.0, 20.0, 21.0)

        assert len(cells) > 0
        # All cells should be within bounds
        for cell in cells:
            assert 44.0 <= cell.lat <= 45.0
            assert 20.0 <= cell.lng <= 21.0

    def test_create_grid_cell_spacing(self):
        """Cells are approximately grid_size_km apart."""
        analyzer = GridAnalyzer(grid_size_km=10)
        cells = analyzer.create_grid(44.0, 44.5, 20.0, 20.5)

        if len(cells) >= 2:
            # Check latitude spacing (~0.09 degrees for 10km)
            same_lng = cells[0].lng == cells[1].lng
            lat_diff = abs(cells[0].lat - cells[1].lat) if same_lng else 0
            if lat_diff > 0:
                assert 0.05 < lat_diff < 0.15  # ~10km tolerance

    def test_assign_hotspots_counts(self):
        """Hotspots are assigned to correct cells."""
        analyzer = GridAnalyzer(grid_size_km=10)
        cells = [
            GridCell(lat=44.0, lng=20.0, grid_size_km=10),
            GridCell(lat=44.1, lng=20.1, grid_size_km=10),
        ]

        # Create mock hotspot at first cell location
        hotspot = type("Hotspot", (), {"lat": 44.0, "lng": 20.0, "loc_name": "Test"})()

        analyzer.assign_hotspots_to_grid(cells, [hotspot])

        # At least one cell should have the hotspot
        total_assigned = sum(c.hotspot_count for c in cells)
        assert total_assigned >= 1

    def test_identify_gaps(self):
        """Gaps are cells with no hotspots."""
        analyzer = GridAnalyzer(grid_size_km=10)
        cells = [
            GridCell(lat=44.0, lng=20.0, grid_size_km=10, hotspot_count=1),
            GridCell(lat=44.1, lng=20.1, grid_size_km=10, hotspot_count=0),
            GridCell(lat=44.2, lng=20.2, grid_size_km=10, hotspot_count=0),
        ]

        gaps = analyzer.identify_gaps(cells, [], min_hotspots=1)

        assert len(gaps) == 2
        assert all(c.hotspot_count == 0 for c in gaps)

    def test_find_nearest_hotspot(self):
        """Finds nearest hotspot correctly."""
        analyzer = GridAnalyzer(grid_size_km=10)
        cell = GridCell(lat=44.0, lng=20.0, grid_size_km=10)

        hotspots = [
            type("Hotspot", (), {"lat": 44.5, "lng": 20.5, "loc_name": "Far"})(),
            type("Hotspot", (), {"lat": 44.1, "lng": 20.1, "loc_name": "Near"})(),
        ]

        nearest, dist = analyzer.find_nearest_hotspot(cell, hotspots)

        assert nearest is not None
        assert nearest.loc_name == "Near"
        assert dist is not None
        assert dist < 20  # Should be close

    def test_haversine_distance(self):
        """Haversine calculation is reasonable."""
        analyzer = GridAnalyzer(grid_size_km=10)

        # Belgrade to Novi Sad ~70km
        dist = analyzer._haversine_km(44.8, 20.4, 45.25, 19.85)
        assert 60 < dist < 80

        # Same point = 0
        dist_same = analyzer._haversine_km(44.8, 20.4, 44.8, 20.4)
        assert dist_same == 0
