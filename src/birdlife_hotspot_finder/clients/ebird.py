"""eBird API client for hotspot and checklist data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx


@dataclass
class Hotspot:
    """eBird hotspot location."""

    loc_id: str
    loc_name: str
    country_code: str
    subnational1_code: str | None
    lat: float
    lng: float
    latest_obs_dt: str | None = None
    num_species_all_time: int | None = None


@dataclass
class ChecklistStats:
    """Checklist statistics for a region or hotspot."""

    location_id: str
    num_checklists: int
    num_species: int


class EBirdClient:
    """Async client for eBird API 2.0 - hotspot and checklist endpoints."""

    BASE_URL = "https://api.ebird.org/v2"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"x-ebirdapitoken": self.api_key},
                timeout=30.0,
            )
        return self._client

    async def get_hotspots_in_region(self, region_code: str) -> list[Hotspot]:
        """Get all hotspots in a region.

        Args:
            region_code: eBird region code (e.g., 'RS' for Serbia, 'US-NY')

        Returns:
            List of Hotspot objects
        """
        client = await self._get_client()
        response = await client.get(
            f"/ref/hotspot/{region_code}",
            params={"fmt": "json"},
        )
        response.raise_for_status()

        return [
            Hotspot(
                loc_id=h["locId"],
                loc_name=h["locName"],
                country_code=h["countryCode"],
                subnational1_code=h.get("subnational1Code"),
                lat=h["lat"],
                lng=h["lng"],
                latest_obs_dt=h.get("latestObsDt"),
                num_species_all_time=h.get("numSpeciesAllTime"),
            )
            for h in response.json()
        ]

    async def get_nearby_hotspots(
        self,
        lat: float,
        lng: float,
        dist: int = 25,
    ) -> list[Hotspot]:
        """Get hotspots near coordinates.

        Args:
            lat: Latitude
            lng: Longitude
            dist: Search radius in km (default 25, max 50)

        Returns:
            List of nearby Hotspot objects
        """
        client = await self._get_client()
        response = await client.get(
            "/ref/hotspot/geo",
            params={"lat": lat, "lng": lng, "dist": dist, "fmt": "json"},
        )
        response.raise_for_status()

        return [
            Hotspot(
                loc_id=h["locId"],
                loc_name=h["locName"],
                country_code=h["countryCode"],
                subnational1_code=h.get("subnational1Code"),
                lat=h["lat"],
                lng=h["lng"],
                latest_obs_dt=h.get("latestObsDt"),
                num_species_all_time=h.get("numSpeciesAllTime"),
            )
            for h in response.json()
        ]

    async def get_hotspot_info(self, loc_id: str) -> dict[str, Any]:
        """Get detailed info for a specific hotspot.

        Args:
            loc_id: eBird location ID (e.g., 'L123456')

        Returns:
            Hotspot info dict
        """
        client = await self._get_client()
        response = await client.get(f"/ref/hotspot/info/{loc_id}")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def get_recent_checklists(
        self,
        region_code: str,
        max_results: int = 200,
    ) -> list[dict[str, Any]]:
        """Get recent checklists in a region.

        Args:
            region_code: eBird region code
            max_results: Maximum number of checklists to return

        Returns:
            List of checklist summaries
        """
        client = await self._get_client()
        response = await client.get(
            f"/product/lists/{region_code}",
            params={"maxResults": max_results},
        )
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    async def get_region_stats(
        self,
        region_code: str,
    ) -> dict[str, Any]:
        """Get observation stats for a region.

        Args:
            region_code: eBird region code

        Returns:
            Region statistics including checklist counts
        """
        client = await self._get_client()
        response = await client.get(f"/product/stats/{region_code}")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
