"""JSON file-based cache implementation."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .interface import CacheInterface


class JsonFileCache(CacheInterface):
    """Simple JSON file cache for local development."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.path / f"{safe_key}.json"

    def get(self, key: str) -> Any | None:
        file_path = self._key_to_path(key)
        if not file_path.exists():
            return None

        data = json.loads(file_path.read_text())
        expires_at = datetime.fromisoformat(data["expires_at"])

        if datetime.now(UTC).replace(tzinfo=None) > expires_at:
            file_path.unlink()
            return None

        return data["value"]

    def set(self, key: str, value: Any, ttl_days: int = 30) -> None:
        file_path = self._key_to_path(key)
        now = datetime.now(UTC).replace(tzinfo=None)
        expires_at = now + timedelta(days=ttl_days)

        data = {
            "key": key,
            "value": value,
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat(),
        }

        file_path.write_text(json.dumps(data, indent=2))

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        file_path = self._key_to_path(key)
        if file_path.exists():
            file_path.unlink()

    def clear(self) -> None:
        for file_path in self.path.glob("*.json"):
            file_path.unlink()
