"""Data models for volunteer-hotspot-finder."""

from .location import CoverageExtensions, Location
from .result import FinderMeta, FinderResult

__all__ = ["CoverageExtensions", "FinderMeta", "FinderResult", "Location"]
