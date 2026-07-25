"""API response envelope for finder results."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .location import Location


class FinderMeta(BaseModel):
    """Metadata for finder results (query context only)."""

    result_type: Literal["coverage-gaps", "coverage-stats"] = Field(alias="resultType")
    query_timestamp: datetime = Field(alias="queryTimestamp")
    grid_size_km: int = Field(alias="gridSizeKm")
    region: str | None = None
    lat: float | None = None
    lng: float | None = None
    radius_km: float | None = Field(default=None, alias="radiusKm")

    model_config = {"populate_by_name": True}


class FinderResult(BaseModel):
    """API response envelope following {data, meta} convention."""

    data: list[Location]
    meta: FinderMeta

    def to_response_dict(self) -> dict[str, Any]:
        """Export as API response dict."""
        return {
            "data": [loc.to_schema_dict() for loc in self.data],
            "meta": self.meta.model_dump(by_alias=True, exclude_none=True, mode="json"),
        }
