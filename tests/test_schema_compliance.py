"""Tests that verify model output matches birdlife-schema."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from birdlife_hotspot_finder.models import CoverageExtensions, Location

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


@pytest.fixture
def schema_validator(location_schema: dict) -> Draft202012Validator:
    """Create a validator for Location schema."""
    return Draft202012Validator(location_schema)


class TestLocationSchemaCompliance:
    """Verify Location model output validates against JSON schema."""

    def test_minimal_location_validates(self, schema_validator: Draft202012Validator):
        """Minimal Location with only required fields."""
        loc = Location(
            locationID="test-uuid-1234",
            slug="test-location",
            name="Test Location",
            geodeticDatum="WGS84",
        )
        output = loc.to_schema_dict()
        errors = list(schema_validator.iter_errors(output))
        assert not errors, f"Schema validation failed: {errors}"

    def test_full_location_validates(self, schema_validator: Draft202012Validator):
        """Location with all fields populated."""
        loc = Location(
            locationID="test-uuid-5678",
            slug="belgrade-wetlands",
            name="Belgrade Wetlands",
            geodeticDatum="WGS84",
            decimalLatitude=44.8,
            decimalLongitude=20.4,
            coordinateUncertaintyInMeters=5000,
            country="Serbia",
            countryCode="RS",
            locality="Near Danube confluence",
            habitat=["wetland", "riparian"],
            extensions={
                "coverage.gapType": "spatial",
                "coverage.priorityScore": "0.85",
            },
        )
        output = loc.to_schema_dict()
        errors = list(schema_validator.iter_errors(output))
        assert not errors, f"Schema validation failed: {errors}"

    def test_grid_cell_validates(self, schema_validator: Draft202012Validator):
        """Grid cell created via factory validates."""
        coverage = CoverageExtensions(
            gap_type="spatial",
            priority_score=0.75,
            checklist_count=0,
            reasoning="No checklists in 12 months",
        )
        loc = Location.create_grid_cell(lat=44.8, lng=20.4, coverage=coverage)
        output = loc.to_schema_dict()
        errors = list(schema_validator.iter_errors(output))
        assert not errors, f"Schema validation failed: {errors}"

    def test_extensions_are_string_values(self, schema_validator: Draft202012Validator):
        """Schema requires extensions values to be strings."""
        coverage = CoverageExtensions(
            gap_type="temporal",
            priority_score=0.5,
            checklist_count=3,
            nearest_hotspot_distance_km=12.5,
        )
        extensions = coverage.to_extensions_dict()
        for key, value in extensions.items():
            assert isinstance(value, str), f"Extension {key} value must be string"
            assert "." in key, f"Extension key {key} must be namespaced"
