"""Volunteer Hotspot Finder - identify data gaps for citizen science coverage."""

__version__ = "0.1.0-dev"

from .config import Config
from .finder import HotspotFinder

__all__ = ["Config", "HotspotFinder", "__version__"]
