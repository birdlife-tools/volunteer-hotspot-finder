"""eBird API client for hotspot and checklist data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EBirdClient:
    """Client for eBird API 2.0."""

    api_key: str
    base_url: str = "https://api.ebird.org/v2"

    async def get_hotspots(self, region: str) -> list[dict[str, object]]:
        """Get hotspots in a region."""
        raise NotImplementedError("Coming in Phase 2")

    async def get_recent_checklists(
        self, region: str, days: int = 30
    ) -> list[dict[str, object]]:
        """Get recent checklists in a region."""
        raise NotImplementedError("Coming in Phase 2")
