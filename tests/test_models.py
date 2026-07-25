"""Tests for data models."""

from datetime import date, datetime

import pytest

from birdlife_hotspot_finder.models import (
    CoverageExtensions,
    FinderMeta,
    FinderResult,
    Location,
)


class TestCoverageExtensions:
    """Tests for CoverageExtensions model."""

    def test_to_extensions_dict_converts_to_strings(self):
        """All values should be converted to strings."""
        ext = CoverageExtensions(
            gap_type="spatial",
            priority_score=0.85,
            checklist_count=0,
            last_survey=date(2025, 6, 15),
            reasoning="No recent data",
        )
        result = ext.to_extensions_dict()

        assert result["coverage.gapType"] == "spatial"
        assert result["coverage.priorityScore"] == "0.85"
        assert result["coverage.checklistCount"] == "0"
        assert result["coverage.lastSurvey"] == "2025-06-15"
        assert result["coverage.reasoning"] == "No recent data"

    def test_none_values_excluded(self):
        """None values should not appear in output."""
        ext = CoverageExtensions(gap_type="spatial")
        result = ext.to_extensions_dict()

        assert "coverage.gapType" in result
        assert "coverage.priorityScore" not in result
        assert "coverage.checklistCount" not in result

    def test_priority_score_validation(self):
        """Priority score must be between 0 and 1."""
        with pytest.raises(ValueError):
            CoverageExtensions(priority_score=1.5)
        with pytest.raises(ValueError):
            CoverageExtensions(priority_score=-0.1)

        valid = CoverageExtensions(priority_score=0.0)
        assert valid.priority_score == 0.0
        valid = CoverageExtensions(priority_score=1.0)
        assert valid.priority_score == 1.0


class TestLocation:
    """Tests for Location model."""

    def test_create_with_aliases(self):
        """Can create Location using schema field names."""
        loc = Location(
            locationID="uuid-123",
            slug="test",
            name="Test",
            geodeticDatum="WGS84",
            decimalLatitude=44.8,
            decimalLongitude=20.4,
        )
        assert loc.location_id == "uuid-123"
        assert loc.decimal_latitude == 44.8

    def test_to_schema_dict_uses_aliases(self):
        """Output should use schema field names."""
        loc = Location(
            locationID="uuid-456",
            slug="test-loc",
            name="Test Location",
            geodeticDatum="WGS84",
            decimalLatitude=44.8,
        )
        output = loc.to_schema_dict()

        assert "locationID" in output
        assert "decimalLatitude" in output
        assert "location_id" not in output
        assert "decimal_latitude" not in output

    def test_create_grid_cell(self):
        """Grid cell factory creates valid Location."""
        coverage = CoverageExtensions(
            gap_type="spatial",
            priority_score=0.9,
            checklist_count=0,
        )
        loc = Location.create_grid_cell(lat=44.8, lng=20.4, coverage=coverage)

        assert loc.decimal_latitude == 44.8
        assert loc.decimal_longitude == 20.4
        assert loc.geodetic_datum == "WGS84"
        assert loc.coordinate_uncertainty_in_meters == 5000  # 10km / 2
        assert "grid" in loc.slug
        assert loc.extensions["coverage.gapType"] == "spatial"

    def test_grid_cell_deterministic_id(self):
        """Same coordinates produce same UUID."""
        loc1 = Location.create_grid_cell(lat=44.8, lng=20.4)
        loc2 = Location.create_grid_cell(lat=44.8, lng=20.4)
        loc3 = Location.create_grid_cell(lat=44.8, lng=20.4, grid_size_km=5)

        assert loc1.location_id == loc2.location_id
        assert loc1.location_id != loc3.location_id  # Different grid size


class TestFinderResult:
    """Tests for FinderResult envelope."""

    def test_to_response_dict(self):
        """Response dict follows API convention."""
        locations = [
            Location(
                locationID="uuid-1",
                slug="gap-1",
                name="Gap 1",
                geodeticDatum="WGS84",
                extensions={"coverage.gapType": "spatial"},
            ),
        ]
        meta = FinderMeta(
            resultType="coverage-gaps",
            queryTimestamp=datetime(2026, 7, 25, 12, 0, 0),
            gridSizeKm=10,
            region="RS",
        )
        result = FinderResult(data=locations, meta=meta)
        response = result.to_response_dict()

        assert "data" in response
        assert "meta" in response
        assert len(response["data"]) == 1
        assert response["data"][0]["locationID"] == "uuid-1"
        assert response["meta"]["resultType"] == "coverage-gaps"
        assert response["meta"]["gridSizeKm"] == 10
