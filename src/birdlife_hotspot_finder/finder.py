"""Core HotspotFinder implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from .analyzers.grid import GridAnalyzer
from .cache.interface import CacheInterface
from .cache.json_file import JsonFileCache
from .cache.sqlite import SqliteCache
from .clients.ebird import EBirdClient
from .config import CacheType, Config
from .models.location import CoverageExtensions, Location
from .models.result import FinderMeta, FinderResult

if TYPE_CHECKING:
    pass


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
        grid_size_km: int = 10,
    ) -> None:
        self._ebird = ebird
        self._cache = cache
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

        return cls(
            ebird=ebird,
            cache=cache,
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

    async def find_gaps(
        self,
        region: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float = 25,
        limit: int = 10,
    ) -> FinderResult:
        """Find coverage gaps in a region or around coordinates.

        Args:
            region: eBird region code (e.g., 'RS', 'US-NY')
            lat, lng: Center coordinates for nearby search
            radius_km: Search radius for nearby mode (default 25km)
            limit: Maximum results to return

        Returns:
            FinderResult with Location entities and coverage extensions
        """
        if region:
            return await self._find_gaps_in_region(region, limit)
        elif lat is not None and lng is not None:
            return await self._find_gaps_nearby(lat, lng, radius_km, limit)
        else:
            raise ValueError("Provide either region or lat/lng coordinates")

    async def _find_gaps_in_region(self, region: str, limit: int) -> FinderResult:
        """Find gaps in a region using grid analysis."""
        # Get region bounds
        if region not in REGION_BOUNDS:
            raise ValueError(
                f"Unknown region: {region}. "
                f"Supported: {', '.join(REGION_BOUNDS.keys())}"
            )

        min_lat, max_lat, min_lng, max_lng = REGION_BOUNDS[region]

        # Get hotspots (cached)
        hotspots_data = await self._get_hotspots_cached(region)
        hotspots = [
            type(
                "Hotspot",
                (),
                {
                    "loc_id": h["loc_id"],
                    "loc_name": h["loc_name"],
                    "lat": h["lat"],
                    "lng": h["lng"],
                },
            )()
            for h in hotspots_data
        ]

        # Create grid
        cells = self._grid_analyzer.create_grid(min_lat, max_lat, min_lng, max_lng)

        # Assign hotspots to cells
        self._grid_analyzer.assign_hotspots_to_grid(cells, hotspots)

        # Find gaps
        gaps = self._grid_analyzer.identify_gaps(cells, hotspots, min_hotspots=1)

        # Convert to Location entities
        locations: list[Location] = []
        for cell in gaps[:limit]:
            coverage = CoverageExtensions(
                gap_type="spatial",
                priority_score=self._calculate_priority(cell),
                checklist_count=cell.checklist_count,
                reasoning="No eBird hotspots in this grid cell",
                nearest_hotspot_name=(
                    cell.nearest_hotspot.loc_name if cell.nearest_hotspot else None
                ),
                nearest_hotspot_distance_km=cell.nearest_hotspot_distance_km,
            )
            loc = Location.create_grid_cell(
                lat=cell.lat,
                lng=cell.lng,
                grid_size_km=self._grid_size_km,
                coverage=coverage,
            )
            locations.append(loc)

        meta = FinderMeta(
            result_type="coverage-gaps",
            query_timestamp=datetime.now(UTC),
            grid_size_km=self._grid_size_km,
            region=region,
        )

        return FinderResult(data=locations, meta=meta)

    async def _find_gaps_nearby(
        self, lat: float, lng: float, radius_km: float, limit: int
    ) -> FinderResult:
        """Find gaps near coordinates."""
        # Get nearby hotspots
        hotspots = await self._ebird.get_nearby_hotspots(lat, lng, dist=int(radius_km))

        # Create grid around coordinates
        lat_offset = radius_km / 111.0
        lng_offset = radius_km / (111.0 * abs(lat) / 90 if lat != 0 else 111.0)

        cells = self._grid_analyzer.create_grid(
            lat - lat_offset,
            lat + lat_offset,
            lng - lng_offset,
            lng + lng_offset,
        )

        # Assign and find gaps
        self._grid_analyzer.assign_hotspots_to_grid(cells, hotspots)
        gaps = self._grid_analyzer.identify_gaps(cells, hotspots, min_hotspots=1)

        # Convert to Location entities
        locations: list[Location] = []
        for cell in gaps[:limit]:
            coverage = CoverageExtensions(
                gap_type="spatial",
                priority_score=self._calculate_priority(cell),
                checklist_count=cell.checklist_count,
                reasoning="No eBird hotspots in this grid cell",
                nearest_hotspot_name=(
                    cell.nearest_hotspot.loc_name if cell.nearest_hotspot else None
                ),
                nearest_hotspot_distance_km=cell.nearest_hotspot_distance_km,
            )
            loc = Location.create_grid_cell(
                lat=cell.lat,
                lng=cell.lng,
                grid_size_km=self._grid_size_km,
                coverage=coverage,
            )
            locations.append(loc)

        meta = FinderMeta(
            result_type="coverage-gaps",
            query_timestamp=datetime.now(UTC),
            grid_size_km=self._grid_size_km,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        )

        return FinderResult(data=locations, meta=meta)

    def _calculate_priority(self, cell: Any) -> float:
        """Calculate priority score for a gap cell.

        Higher score = more urgent gap to fill.
        Based on: distance to nearest hotspot (closer = higher priority),
        accessibility potential.
        """
        if cell.nearest_hotspot_distance_km is None:
            return 0.5  # Unknown distance

        dist = cell.nearest_hotspot_distance_km

        # Cells closer to existing hotspots are easier to reach
        # Normalize: 0-10km = high priority, 50km+ = lower priority
        if dist <= 10:
            return 0.9
        elif dist <= 20:
            return 0.7
        elif dist <= 30:
            return 0.5
        elif dist <= 50:
            return 0.3
        else:
            return 0.2

    async def close(self) -> None:
        """Close resources."""
        await self._ebird.close()
