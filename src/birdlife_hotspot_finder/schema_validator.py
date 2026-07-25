"""Validate data against birdlife-schema (JSON Schema + Avro)."""

import json
from pathlib import Path
from typing import Any

from birdlife_hotspot_finder.models.location import Location
from birdlife_hotspot_finder.models.result import FinderResult

SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas" / "birdlife-schema"
AVRO_DIR = SCHEMA_DIR / "avro"
JSON_SCHEMA_DIR = SCHEMA_DIR / "json-schema"


def get_schema_version() -> str:
    """Get current birdlife-schema version."""
    version_file = SCHEMA_DIR / "VERSION"
    if not version_file.exists():
        raise FileNotFoundError("birdlife-schema VERSION not found")
    return version_file.read_text().strip()


def load_json_schema(name: str) -> dict[str, Any]:
    """Load JSON schema from birdlife-schema submodule."""
    schema_path = JSON_SCHEMA_DIR / f"{name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    result: dict[str, Any] = json.loads(schema_path.read_text())
    return result


def load_avro_schema(name: str) -> dict[str, Any]:
    """Load and parse Avro schema from birdlife-schema submodule."""
    try:
        import fastavro
    except ImportError as e:
        raise ImportError("fastavro required for Avro validation") from e

    schema_path = AVRO_DIR / f"{name}.avsc"
    if not schema_path.exists():
        raise FileNotFoundError(f"Avro schema not found: {schema_path}")
    parsed = fastavro.parse_schema(json.loads(schema_path.read_text()))
    if not isinstance(parsed, dict):
        raise TypeError(f"Expected dict schema, got {type(parsed)}")
    return parsed


_LOCATION_AVRO_SCHEMA: dict[str, Any] | None = None


def _get_location_avro_schema() -> dict[str, Any]:
    """Get cached Avro location schema."""
    global _LOCATION_AVRO_SCHEMA
    if _LOCATION_AVRO_SCHEMA is None:
        _LOCATION_AVRO_SCHEMA = load_avro_schema("location")
    return _LOCATION_AVRO_SCHEMA


def location_to_avro_record(location: Location) -> dict[str, Any]:
    """Convert Location model to Avro-compatible record."""
    return {
        "locationID": location.location_id,
        "slug": location.slug,
        "name": location.name,
        "geodeticDatum": location.geodetic_datum or "WGS84",
        "decimalLatitude": location.decimal_latitude,
        "decimalLongitude": location.decimal_longitude,
        "coordinateUncertaintyInMeters": location.coordinate_uncertainty_in_meters,
        "country": location.country,
        "countryCode": location.country_code,
        "locality": location.locality,
        "habitat": location.habitat,
        "extensions": location.extensions if location.extensions else None,
    }


def validate_location_avro(location: Location) -> list[str]:
    """Validate Location against Avro schema. Returns list of errors."""
    try:
        import fastavro
    except ImportError:
        return ["fastavro not installed"]

    errors: list[str] = []
    try:
        record = location_to_avro_record(location)
        fastavro.validate(record, _get_location_avro_schema())
    except Exception as e:
        errors.append(f"{location.name}: {e}")
    return errors


def validate_result_avro(result: FinderResult) -> list[str]:
    """Validate all locations in FinderResult against Avro schema."""
    errors: list[str] = []
    for location in result.data:
        errors.extend(validate_location_avro(location))
    return errors
