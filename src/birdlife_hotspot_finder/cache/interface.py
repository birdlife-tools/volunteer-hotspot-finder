"""Cache interface for hotspot data storage."""

from abc import ABC, abstractmethod
from typing import Any


class CacheInterface(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Retrieve a value from cache. Returns None if not found or expired."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl_days: int = 30) -> None:
        """Store a value in cache with TTL in days."""

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a non-expired key exists in cache."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a key from cache."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from cache."""
