"""BirdLife Resolution API client for location resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ResolvedLocation:
    """Resolved location from Resolution API."""

    location_id: str
    slug: str
    name: str | None = None
    country_code: str | None = None


class ResolutionClient:
    """Client for BirdLife Resolution API.

    Used to resolve coordinates to canonical Location entities.
    Falls back gracefully if API is unavailable.
    """

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def resolve_location(
        self,
        lat: float,
        lng: float,
        name: str | None = None,
    ) -> ResolvedLocation | None:
        """Resolve coordinates to a canonical Location.

        Args:
            lat: Latitude
            lng: Longitude
            name: Optional name hint

        Returns:
            ResolvedLocation if successful, None if API unavailable
        """
        try:
            client = await self._get_client()
            payload: dict[str, Any] = {
                "decimalLatitude": lat,
                "decimalLongitude": lng,
            }
            if name:
                payload["name"] = name

            response = await client.post("/location/resolve", json=payload)
            response.raise_for_status()

            data = response.json()
            # API returns {data: [...], meta: {...}}
            if data.get("data") and len(data["data"]) > 0:
                loc = data["data"][0]
                return ResolvedLocation(
                    location_id=loc["locationID"],
                    slug=loc["slug"],
                    name=loc.get("name"),
                    country_code=loc.get("countryCode"),
                )
            return None

        except (httpx.HTTPError, KeyError):
            # API unavailable or error - caller should fall back to local UUID
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
