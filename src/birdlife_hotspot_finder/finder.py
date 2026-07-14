"""Core HotspotFinder implementation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .clients.ebird import EBirdClient


@dataclass
class FinderConfig:
    """Configuration for HotspotFinder."""

    grid_size_km: int = 10


class HotspotFinder:
    """Find coverage gaps in eBird data for volunteer survey prioritization."""

    def __init__(
        self,
        ebird: EBirdClient | None = None,
        grid_size_km: int = 10,
    ) -> None:
        self._ebird = ebird
        self._config = FinderConfig(grid_size_km=grid_size_km)

    @classmethod
    def from_env(cls) -> HotspotFinder:
        """Create finder with clients configured from environment variables."""
        from .clients.ebird import EBirdClient

        api_key = os.environ.get("EBIRD_API_KEY")
        if not api_key:
            raise ValueError("EBIRD_API_KEY environment variable required")
        return cls(ebird=EBirdClient(api_key=api_key))

    async def find_gaps(
        self,
        region: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float = 25,
        limit: int = 10,
    ) -> dict:
        """Find coverage gaps in a region or around coordinates.

        Args:
            region: eBird region code (e.g., 'RS', 'US-NY')
            lat, lng: Center coordinates for nearby search
            radius_km: Search radius (default 25km)
            limit: Maximum results

        Returns:
            API response envelope with Location entities and coverage extensions
        """
        raise NotImplementedError("Coming in Phase 2-3")
