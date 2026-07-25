"""Serializer protocol for output formats."""

from typing import Protocol

from birdlife_hotspot_finder.models.result import FinderResult


class Serializer(Protocol):
    """Protocol for result serializers."""

    def serialize(self, result: FinderResult) -> str:
        """Serialize a FinderResult to output format."""
        ...
