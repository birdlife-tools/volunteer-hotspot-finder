"""Tests for serializers."""

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from birdlife_hotspot_finder.models.location import CoverageExtensions, Location
from birdlife_hotspot_finder.models.result import FinderMeta, FinderResult
from birdlife_hotspot_finder.serializers import (
    CsvSerializer,
    GeoJsonSerializer,
    JsonSerializer,
)

SCHEMA_PATH = (
    Path(__file__).parent.parent / "schemas" / "birdlife-schema" / "json-schema"
)


@pytest.fixture
def location_schema() -> dict:
    """Load the Location JSON schema."""
    schema_file = SCHEMA_PATH / "location.json"
    if not schema_file.exists():
        pytest.skip("birdlife-schema submodule not initialized")
    return json.loads(schema_file.read_text())


def create_sample_result() -> FinderResult:
    """Create a sample FinderResult for testing."""
    coverage = CoverageExtensions(
        gap_type="spatial",
        priority_score=0.85,
        checklist_count=0,
        reasoning="No eBird hotspots in this grid cell",
        nearest_hotspot_name="Test Hotspot",
        nearest_hotspot_distance_km=5.5,
    )
    location = Location(
        location_id="test-uuid-123",
        slug="grid-44-80n-20-40e",
        name="Grid cell 44.80N 20.40E",
        geodetic_datum="WGS84",
        decimal_latitude=44.8,
        decimal_longitude=20.4,
        coordinate_uncertainty_in_meters=5000,
        extensions=coverage.to_extensions_dict(),
    )
    meta = FinderMeta(
        result_type="coverage-gaps",
        query_timestamp=datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC),
        grid_size_km=10,
        region="RS",
    )
    return FinderResult(data=[location], meta=meta)


class TestJsonSerializer:
    """Tests for JsonSerializer."""

    def test_serialize_returns_valid_json(self):
        """Output is valid JSON."""
        result = create_sample_result()
        serializer = JsonSerializer()
        output = serializer.serialize(result)

        parsed = json.loads(output)
        assert "data" in parsed
        assert "meta" in parsed

    def test_serialize_follows_api_convention(self):
        """Output follows {data, meta} envelope."""
        result = create_sample_result()
        output = JsonSerializer().serialize(result)
        parsed = json.loads(output)

        assert isinstance(parsed["data"], list)
        assert len(parsed["data"]) == 1
        assert parsed["data"][0]["locationID"] == "test-uuid-123"
        assert parsed["meta"]["resultType"] == "coverage-gaps"
        assert parsed["meta"]["gridSizeKm"] == 10

    def test_serialize_includes_extensions(self):
        """Extensions are included in output."""
        result = create_sample_result()
        output = JsonSerializer().serialize(result)
        parsed = json.loads(output)

        extensions = parsed["data"][0]["extensions"]
        assert extensions["coverage.gapType"] == "spatial"
        assert extensions["coverage.priorityScore"] == "0.85"

    def test_indent_option(self):
        """Indent option controls formatting."""
        result = create_sample_result()

        compact = JsonSerializer(indent=None).serialize(result)
        pretty = JsonSerializer(indent=2).serialize(result)

        assert len(pretty) > len(compact)
        assert "\n" in pretty
        assert "\n" not in compact

    def test_locations_validate_against_schema(self, location_schema):
        """Each location in JSON output validates against birdlife-schema."""
        result = create_sample_result()
        output = JsonSerializer().serialize(result)
        parsed = json.loads(output)

        validator = Draft202012Validator(location_schema)
        for loc in parsed["data"]:
            errors = list(validator.iter_errors(loc))
            assert not errors, f"Location failed schema validation: {errors}"


class TestCsvSerializer:
    """Tests for CsvSerializer."""

    def test_serialize_returns_valid_csv(self):
        """Output is valid CSV."""
        result = create_sample_result()
        output = CsvSerializer().serialize(result)

        reader = csv.reader(io.StringIO(output))
        rows = list(reader)

        assert len(rows) == 2  # Header + 1 data row

    def test_csv_has_expected_columns(self):
        """CSV has all expected columns."""
        result = create_sample_result()
        output = CsvSerializer().serialize(result)

        reader = csv.reader(io.StringIO(output))
        header = next(reader)

        expected = [
            "locationID",
            "name",
            "latitude",
            "longitude",
            "gapType",
            "priorityScore",
        ]
        for col in expected:
            assert col in header

    def test_csv_data_values(self):
        """CSV data values are correct."""
        result = create_sample_result()
        output = CsvSerializer().serialize(result)

        reader = csv.DictReader(io.StringIO(output))
        row = next(reader)

        assert row["locationID"] == "test-uuid-123"
        assert row["latitude"] == "44.8"
        assert row["longitude"] == "20.4"
        assert row["gapType"] == "spatial"
        assert row["priorityScore"] == "0.85"
        assert row["nearestHotspot"] == "Test Hotspot"


class TestGeoJsonSerializer:
    """Tests for GeoJsonSerializer."""

    def test_serialize_returns_valid_geojson(self):
        """Output is valid GeoJSON FeatureCollection."""
        result = create_sample_result()
        output = GeoJsonSerializer().serialize(result)
        parsed = json.loads(output)

        assert parsed["type"] == "FeatureCollection"
        assert "features" in parsed
        assert isinstance(parsed["features"], list)

    def test_geojson_feature_structure(self):
        """Features have correct GeoJSON structure."""
        result = create_sample_result()
        output = GeoJsonSerializer().serialize(result)
        parsed = json.loads(output)

        feature = parsed["features"][0]
        assert feature["type"] == "Feature"
        assert "geometry" in feature
        assert "properties" in feature

    def test_geojson_geometry(self):
        """Geometry is Point with correct coordinates."""
        result = create_sample_result()
        output = GeoJsonSerializer().serialize(result)
        parsed = json.loads(output)

        geometry = parsed["features"][0]["geometry"]
        assert geometry["type"] == "Point"
        # GeoJSON is [lng, lat]
        assert geometry["coordinates"] == [20.4, 44.8]

    def test_geojson_properties(self):
        """Properties include flattened coverage data."""
        result = create_sample_result()
        output = GeoJsonSerializer().serialize(result)
        parsed = json.loads(output)

        props = parsed["features"][0]["properties"]
        assert props["locationID"] == "test-uuid-123"
        assert props["name"] == "Grid cell 44.80N 20.40E"
        assert props["gapType"] == "spatial"
        assert props["priorityScore"] == 0.85  # Parsed as float
        assert props["checklistCount"] == 0  # Parsed as int
        assert props["nearestHotspotName"] == "Test Hotspot"

    def test_geojson_collection_properties(self):
        """FeatureCollection has metadata properties."""
        result = create_sample_result()
        output = GeoJsonSerializer().serialize(result)
        parsed = json.loads(output)

        props = parsed["properties"]
        assert props["resultType"] == "coverage-gaps"
        assert props["gridSizeKm"] == 10
        assert props["totalGaps"] == 1

    def test_coordinates_order(self):
        """GeoJSON uses [longitude, latitude] order."""
        result = create_sample_result()
        output = GeoJsonSerializer().serialize(result)
        parsed = json.loads(output)

        coords = parsed["features"][0]["geometry"]["coordinates"]
        # First is longitude (20.4), second is latitude (44.8)
        assert coords[0] == 20.4
        assert coords[1] == 44.8
