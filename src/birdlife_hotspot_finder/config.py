"""Configuration for the hotspot finder."""

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheType(StrEnum):
    JSON = "json"
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    NONE = "none"


class Config(BaseSettings):
    """Configuration for Volunteer Hotspot Finder.

    Values can be set via:
    - Environment variables (e.g., EBIRD_API_KEY)
    - .env file
    - Direct instantiation

    Example:
        # From environment variables
        config = Config()

        # From .env file
        config = Config(_env_file=".env")

        # Direct
        config = Config(ebird_api_key="xxx")
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ebird_api_key: str = Field(
        ...,
        description="eBird API key from https://ebird.org/api/keygen",
    )

    cache_type: CacheType = Field(
        default=CacheType.JSON,
        description="Cache implementation: json, sqlite, postgres, or none",
    )
    cache_dir: Path = Field(
        default=Path("./.cache"),
        description="Directory for cache storage (json/sqlite)",
    )
    cache_ttl_days: int = Field(
        default=30,
        description="Cache TTL in days",
        ge=1,
        le=365,
    )

    grid_size_km: int = Field(
        default=10,
        description="Grid cell size in kilometers",
        ge=1,
        le=100,
    )

    postgres_url: str | None = Field(
        default=None,
        description="PostgreSQL connection URL. Required when cache_type=postgres.",
    )

    # Resolution API (optional - falls back to local UUID generation)
    resolution_api_url: str | None = Field(
        default=None,
        description="BirdLife Resolution API URL. Falls back to local UUID generation.",
    )
    resolution_api_token: str | None = Field(
        default=None,
        description="Bearer token for Resolution API (optional).",
    )
