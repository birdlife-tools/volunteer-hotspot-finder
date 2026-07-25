"""SQLite-based cache implementation."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .interface import CacheInterface


class SqliteCache(CacheInterface):
    """SQLite cache for portable single-file storage."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path)
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

    def get(self, key: str) -> Any | None:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        value, expires_at = row
        now = datetime.now(UTC).replace(tzinfo=None)
        if now > datetime.fromisoformat(expires_at):
            self.delete(key)
            return None

        return json.loads(value)

    def set(self, key: str, value: Any, ttl_days: int = 30) -> None:
        conn = self._get_conn()
        now = datetime.now(UTC).replace(tzinfo=None)
        expires_at = now + timedelta(days=ttl_days)

        conn.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, json.dumps(value), expires_at.isoformat(), now.isoformat()),
        )
        conn.commit()

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()

    def clear(self) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM cache")
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
