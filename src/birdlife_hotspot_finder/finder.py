"""Core HotspotFinder implementation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from .analyzers.grid import GridAnalyzer, GridCell
from .cache.interface import CacheInterface
from .cache.json_file import JsonFileCache
from .cache.sqlite import SqliteCache
from .clients.ebird import EBirdClient
from .clients.resolution import ResolutionClient
from .config import CacheType, Config
from .models.location import CoverageExtensions, Location
from .models.result import FinderMeta, FinderResult

# Region bounding boxes (approximate) for common regions
REGION_BOUNDS: dict[str, tuple[float, float, float, float]] = {
    # (min_lat, max_lat, min_lng, max_lng)
    "RS": (42.2, 46.2, 18.8, 23.0),  # Serbia
    "SE": (55.3, 69.1, 10.9, 24.2),  # Sweden
    "ES": (35.9, 43.8, -9.3, 4.3),  # Spain
    "CH": (45.8, 47.8, 5.9, 10.5),  # Switzerland
    "US-NY": (40.5, 45.0, -79.8, -71.9),  # New York
    "US-CA": (32.5, 42.0, -124.4, -114.1),  # California
    "US-TX": (25.8, 36.5, -106.6, -93.5),  # Texas
}


class HotspotFinder:
    """Find coverage gaps in eBird data for volunteer survey prioritization."""

    def __init__(
        self,
        ebird: EBirdClient,
        cache: CacheInterface | None = None,
        resolution: ResolutionClient | None = None,
        grid_size_km: int = 10,
    ) -> None:
        self._ebird = ebird
        self._cache = cache
        self._resolution = resolution
        self._grid_analyzer = GridAnalyzer(grid_size_km=grid_size_km)
        self._grid_size_km = grid_size_km

    @classmethod
    def from_config(cls, config: Config) -> HotspotFinder:
        """Create finder from Config object."""
        ebird = EBirdClient(api_key=config.ebird_api_key)

        cache: CacheInterface | None = None
        if config.cache_type == CacheType.JSON:
            cache = JsonFileCache(config.cache_dir)
        elif config.cache_type == CacheType.SQLITE:
            cache = SqliteCache(config.cache_dir / "hotspot_cache.db")
        elif config.cache_type == CacheType.POSTGRES:
            if not config.postgres_url:
                raise ValueError("postgres_url required when cache_type=postgres")
            from .cache.postgres import PostgresCache

            cache = PostgresCache(config.postgres_url)

        resolution: ResolutionClient | None = None
        if config.resolution_api_url:
            resolution = ResolutionClient(
                base_url=config.resolution_api_url,
                token=config.resolution_api_token,
            )

        return cls(
            ebird=ebird,
            cache=cache,
            resolution=resolution,
            grid_size_km=config.grid_size_km,
        )

    @classmethod
    def from_env(cls) -> HotspotFinder:
        """Create finder with config from environment variables."""
        config = Config()
        return cls.from_config(config)

    def _get_cache_key(self, prefix: str, region: str) -> str:
        """Generate cache key for a region."""
        return f"{prefix}:{region}"

    async def _get_hotspots_cached(self, region: str) -> list[dict[str, Any]]:
        """Get hotspots with caching."""
        cache_key = self._get_cache_key("hotspots", region)

        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cast(list[dict[str, Any]], cached)

        hotspots = await self._ebird.get_hotspots_in_region(region)
        result = [
            {
                "loc_id": h.loc_id,
                "loc_name": h.loc_name,
                "country_code": h.country_code,
                "lat": h.lat,
                "lng": h.lng,
                "latest_obs_dt": h.latest_obs_dt,
                "num_species_all_time": h.num_species_all_time,
            }
            for h in hotspots
        ]

        if self._cache:
            self._cache.set(cache_key, result)

        return result

    async def _resolve_location_id(
        self, lat: float, lng: float, name: str
    ) -> tuple[str, str]:
        """Resolve location to canonical ID via Resolution API or local UUID.

        Returns:
            Tuple of (location_id, slug)
        """
        if self._resolution:
            resolved = await self._resolution.resolve_location(lat, lng, name)
            if resolved:
                return resolved.location_id, resolved.slug

        # Fallback: local UUID5 generation
        ns = uuid.NAMESPACE_DNS
        location_id = str(uuid.uuid5(ns, f"grid:{lat}:{lng}:{self._grid_size_km}"))
        slug = f"grid-{lat:.2f}n-{lng:.2f}e".replace(".", "-")
        return location_id, slug

    async def find_gaps(
        self,
        region: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float = 25,
        bounds: tuple[float, float, float, float] | None = None,
        limit: int = 10,
    ) -> FinderResult:
        """Find coverage gaps in a region or around coordinates.

        Args:
            region: eBird region code (e.g., 'RS', 'US-NY')
            lat, lng: Center coordinates for nearby search
            radius_km: Search radius for nearby mode (default 25km)
            bounds: Custom bounds (min_lat, max_lat, min_lng, max_lng)
            limit: Maximum results to return

        Returns:
            FinderResult with Location entities and coverage extensions
        """
        if bounds:
            return await self._find_gaps_in_bounds(bounds, limit)
        elif region:
            return await self._find_gaps_in_region(region, limit)
        elif lat is not None and lng is not None:
            return await self._find_gaps_nearby(lat, lng, radius_km, limit)
        else:
            raise ValueError("Provide region, lat/lng coordinates, or bounds")

    async def _find_gaps_in_region(self, region: str, limit: int) -> FinderResult:
        """Find gaps in a region using grid analysis."""
        hotspots_data = await self._get_hotspots_cached(region)

        if region in REGION_BOUNDS:
            bounds = REGION_BOUNDS[region]
        elif hotspots_data:
            # Compute bounds from hotspot locations
            lats = [h["lat"] for h in hotspots_data]
            lngs = [h["lng"] for h in hotspots_data]
            bounds = (min(lats), max(lats), min(lngs), max(lngs))
        else:
            raise ValueError(f"No hotspots found for region: {region}")

        return await self._analyze_bounds(
            bounds=bounds,
            hotspots_data=hotspots_data,
            limit=limit,
            region=region,
        )

    async def _find_gaps_in_bounds(
        self,
        bounds: tuple[float, float, float, float],
        limit: int,
    ) -> FinderResult:
        """Find gaps in custom bounds."""
        min_lat, max_lat, min_lng, max_lng = bounds

        # Get hotspots via nearby search at center
        center_lat = (min_lat + max_lat) / 2
        center_lng = (min_lng + max_lng) / 2
        radius = max(
            (max_lat - min_lat) * 111 / 2,
            (max_lng - min_lng) * 111 / 2,
        )

        hotspots = await self._ebird.get_nearby_hotspots(
            center_lat, center_lng, dist=min(int(radius), 50)
        )
        hotspots_data = [
            {
                "loc_id": h.loc_id,
                "loc_name": h.loc_name,
                "country_code": h.country_code,
                "lat": h.lat,
                "lng": h.lng,
                "latest_obs_dt": h.latest_obs_dt,
                "num_species_all_time": h.num_species_all_time,
            }
            for h in hotspots
        ]

        return await self._analyze_bounds(
            bounds=bounds,
            hotspots_data=hotspots_data,
            limit=limit,
        )

    async def _find_gaps_nearby(
        self, lat: float, lng: float, radius_km: float, limit: int
    ) -> FinderResult:
        """Find gaps near coordinates."""
        hotspots = await self._ebird.get_nearby_hotspots(lat, lng, dist=int(radius_km))
        hotspots_data = [
            {
                "loc_id": h.loc_id,
                "loc_name": h.loc_name,
                "country_code": h.country_code,
                "lat": h.lat,
                "lng": h.lng,
                "latest_obs_dt": h.latest_obs_dt,
                "num_species_all_time": h.num_species_all_time,
            }
            for h in hotspots
        ]

        lat_offset = radius_km / 111.0
        lng_offset = radius_km / (111.0 * abs(lat) / 90 if lat != 0 else 111.0)
        bounds = (
            lat - lat_offset,
            lat + lat_offset,
            lng - lng_offset,
            lng + lng_offset,
        )

        return await self._analyze_bounds(
            bounds=bounds,
            hotspots_data=hotspots_data,
            limit=limit,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        )

    async def _analyze_bounds(
        self,
        bounds: tuple[float, float, float, float],
        hotspots_data: list[dict[str, Any]],
        limit: int,
        region: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float | None = None,
    ) -> FinderResult:
        """Core analysis: create grid, find gaps, build result."""
        min_lat, max_lat, min_lng, max_lng = bounds

        # Convert hotspots data to objects for grid analyzer
        hotspots = [
            type(
                "Hotspot",
                (),
                {
                    "loc_id": h["loc_id"],
                    "loc_name": h["loc_name"],
                    "lat": h["lat"],
                    "lng": h["lng"],
                    "num_species_all_time": h.get("num_species_all_time"),
                    "latest_obs_dt": h.get("latest_obs_dt"),
                },
            )()
            for h in hotspots_data
        ]

        # Create grid and analyze
        cells = self._grid_analyzer.create_grid(min_lat, max_lat, min_lng, max_lng)
        self._grid_analyzer.assign_hotspots_to_grid(cells, hotspots)
        gaps = self._grid_analyzer.identify_gaps(cells, hotspots, min_hotspots=1)

        # Calculate priorities with enhanced scoring
        for cell in gaps:
            cell.priority = self._calculate_priority(cell, hotspots_data)

        # Sort by priority (highest first) and limit
        gaps.sort(key=lambda c: c.priority, reverse=True)

        # Convert to Location entities (with Resolution API if configured)
        locations: list[Location] = []
        for cell in gaps[:limit]:
            loc = await self._create_location_from_cell(cell)
            locations.append(loc)

        meta = FinderMeta(
            result_type="coverage-gaps",
            query_timestamp=datetime.now(UTC),
            grid_size_km=self._grid_size_km,
            region=region,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        )

        return FinderResult(data=locations, meta=meta)

    async def _create_location_from_cell(self, cell: GridCell) -> Location:
        """Create Location entity from grid cell, using Resolution API if available."""
        name = f"Grid cell {cell.lat:.2f}N {cell.lng:.2f}E"

        # Resolve via API or generate locally
        location_id, slug = await self._resolve_location_id(cell.lat, cell.lng, name)

        # Build reasoning
        reasoning = self._build_reasoning(cell)

        coverage = CoverageExtensions(
            gap_type="spatial",
            priority_score=round(cell.priority, 2),
            checklist_count=cell.checklist_count,
            reasoning=reasoning,
            nearest_hotspot_name=(
                cell.nearest_hotspot.loc_name if cell.nearest_hotspot else None
            ),
            nearest_hotspot_distance_km=cell.nearest_hotspot_distance_km,
        )

        return Location(
            location_id=location_id,
            slug=slug,
            name=name,
            geodetic_datum="WGS84",
            decimal_latitude=cell.lat,
            decimal_longitude=cell.lng,
            coordinate_uncertainty_in_meters=self._grid_size_km * 1000 // 2,
            extensions=coverage.to_extensions_dict(),
        )

    def _calculate_priority(
        self, cell: GridCell, hotspots_data: list[dict[str, Any]]
    ) -> float:
        """Calculate priority score with enhanced factors.

        Factors:
        - Distance to nearest hotspot (closer = easier to access)
        - Isolation (fewer nearby hotspots = more valuable)
        - Nearby biodiversity (high species count nearby = likely productive)
        - Data staleness (nearby hotspots with old data = higher priority)

        Returns:
            Priority score 0.0-1.0, higher = more urgent
        """
        score = 0.5  # Base score

        # Factor 1: Distance to nearest hotspot (0.0-0.3)
        if cell.nearest_hotspot_distance_km is not None:
            dist = cell.nearest_hotspot_distance_km
            if dist <= 5:
                score += 0.30  # Very accessible
            elif dist <= 10:
                score += 0.25
            elif dist <= 20:
                score += 0.20
            elif dist <= 30:
                score += 0.10
            # Far gaps get no distance bonus (harder to reach)

        # Factor 2: Isolation - count hotspots within 25km (0.0-0.2)
        nearby_count = sum(
            1
            for h in hotspots_data
            if self._haversine(cell.lat, cell.lng, h["lat"], h["lng"]) <= 25
        )
        if nearby_count == 0:
            score += 0.20  # Completely isolated
        elif nearby_count <= 2:
            score += 0.15
        elif nearby_count <= 5:
            score += 0.10

        # Factor 3: Nearby biodiversity (0.0-0.2)
        nearby_species = [
            h.get("num_species_all_time", 0)
            for h in hotspots_data
            if h.get("num_species_all_time")
            and self._haversine(cell.lat, cell.lng, h["lat"], h["lng"]) <= 30
        ]
        if nearby_species:
            avg_species = sum(nearby_species) / len(nearby_species)
            if avg_species >= 100:
                score += 0.20  # High biodiversity area
            elif avg_species >= 50:
                score += 0.15
            elif avg_species >= 20:
                score += 0.10

        # Factor 4: Data staleness (0.0-0.1)
        # Check if nearby hotspots have recent data
        current_year = str(datetime.now().year)
        has_recent_data = any(
            (h.get("latest_obs_dt") or "")[:4] == current_year
            for h in hotspots_data
            if self._haversine(cell.lat, cell.lng, h["lat"], h["lng"]) <= 20
        )
        if not has_recent_data:
            score += 0.10  # No recent data nearby

        return min(score, 1.0)  # Cap at 1.0

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km between two points."""
        import math

        r = 6371
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def _build_reasoning(self, cell: GridCell) -> str:
        """Build human-readable reasoning for gap priority."""
        reasons = ["No eBird hotspots in this grid cell"]

        if cell.nearest_hotspot_distance_km:
            dist = cell.nearest_hotspot_distance_km
            if dist <= 10:
                reasons.append(f"accessible ({dist:.1f}km to nearest hotspot)")
            elif dist > 30:
                reasons.append(f"remote area ({dist:.1f}km to nearest hotspot)")

        if hasattr(cell, "priority") and cell.priority >= 0.8:
            reasons.append("high priority for survey")

        return "; ".join(reasons)

    async def close(self) -> None:
        """Close resources."""
        await self._ebird.close()
        if self._resolution:
            await self._resolution.close()
