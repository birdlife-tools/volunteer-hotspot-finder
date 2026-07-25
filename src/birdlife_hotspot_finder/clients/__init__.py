"""API clients for external data sources."""

from .ebird import EBirdClient, Hotspot
from .resolution import ResolutionClient

__all__ = ["EBirdClient", "Hotspot", "ResolutionClient"]
