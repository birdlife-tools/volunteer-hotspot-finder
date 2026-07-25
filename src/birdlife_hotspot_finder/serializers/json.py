"""JSON serializer for FinderResult."""

import json

from birdlife_hotspot_finder.models.result import FinderResult


class JsonSerializer:
    """Serialize FinderResult to JSON."""

    def __init__(self, indent: int | None = 2) -> None:
        self.indent = indent

    def serialize(self, result: FinderResult) -> str:
        """Serialize to JSON string following API Response Convention."""
        return json.dumps(result.to_response_dict(), indent=self.indent)
