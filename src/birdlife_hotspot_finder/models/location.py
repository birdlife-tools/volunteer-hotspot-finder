"""Location model aligned with birdlife-schema/location.json."""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


class CoverageExtensions(BaseModel):
    """Coverage-specific extensions for Location entities."""

    gap_type: Literal["spatial", "temporal", "effort", "nocturnal"] | None = Field(
        default=None, alias="coverage.gapType"
    )
    priority_score: float | None = Field(
        default=None, alias="coverage.priorityScore", ge=0, le=1
    )
    checklist_count: int | None = Field(
        default=None, alias="coverage.checklistCount", ge=0
    )
    last_survey: date | None = Field(default=None, alias="coverage.lastSurvey")
    reasoning: str | None = Field(default=None, alias="coverage.reasoning")
    suggested_protocol: Literal["stationary", "traveling", "nocturnal"] | None = Field(
        default=None, alias="coverage.suggestedProtocol"
    )
    nearest_hotspot_name: str | None = Field(
        default=None, alias="coverage.nearestHotspotName"
    )
    nearest_hotspot_distance_km: float | None = Field(
        default=None, alias="coverage.nearestHotspotDistanceKm", ge=0
    )

    model_config = {"populate_by_name": True}

    def to_extensions_dict(self) -> dict[str, str]:
        """Convert to flat extensions dict with string values (schema format)."""
        result: dict[str, str] = {}
        for field_name, field_info in type(self).model_fields.items():
            value = getattr(self, field_name)
            if value is not None:
                alias = field_info.alias or field_name
                if isinstance(value, date):
                    result[alias] = value.isoformat()
                else:
                    result[alias] = str(value)
        return result


class Location(BaseModel):
    """Location entity aligned with birdlife-schema/location.json."""

    location_id: str = Field(alias="locationID")
    slug: str
    name: str
    geodetic_datum: str = Field(default="WGS84", alias="geodeticDatum")
    decimal_latitude: float | None = Field(default=None, alias="decimalLatitude")
    decimal_longitude: float | None = Field(default=None, alias="decimalLongitude")
    coordinate_uncertainty_in_meters: int | None = Field(
        default=None, alias="coordinateUncertaintyInMeters"
    )
    country: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    locality: str | None = None
    habitat: list[str] | None = None
    extensions: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str:
        if v:
            return v
        name = info.data.get("name", "")
        return slugify(name) if name else ""

    @classmethod
    def create_grid_cell(
        cls,
        lat: float,
        lng: float,
        grid_size_km: int = 10,
        coverage: CoverageExtensions | None = None,
    ) -> Location:
        """Create a Location for a grid cell center."""
        name = f"Grid cell {lat:.2f}N {lng:.2f}E"
        slug = f"grid-{lat:.2f}n-{lng:.2f}e".replace(".", "-")
        ns = uuid.NAMESPACE_DNS
        location_id = str(uuid.uuid5(ns, f"grid:{lat}:{lng}:{grid_size_km}"))

        extensions: dict[str, str] = {}
        if coverage:
            extensions = coverage.to_extensions_dict()

        return cls(
            locationID=location_id,
            slug=slug,
            name=name,
            decimalLatitude=lat,
            decimalLongitude=lng,
            coordinateUncertaintyInMeters=grid_size_km * 1000 // 2,
            extensions=extensions,
        )

    def to_schema_dict(self) -> dict:
        """Export as schema-compliant dict (using aliases)."""
        return self.model_dump(by_alias=True, exclude_none=True)
