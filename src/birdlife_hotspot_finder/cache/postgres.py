"""PostgreSQL-based cache implementation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from .interface import CacheInterface

if TYPE_CHECKING:
    import psycopg

try:
    import psycopg as psycopg_module
except ImportError:
    psycopg_module = None


class PostgresCache(CacheInterface):
    """PostgreSQL cache for shared/distributed storage.

    Requires psycopg: pip install birdlife-hotspot-finder[postgres]
    """

    def __init__(self, url: str, table_name: str = "hotspot_cache") -> None:
        if psycopg_module is None:
            raise ImportError(
                "psycopg is required for PostgresCache. "
                "Install with: pip install birdlife-hotspot-finder[postgres]"
            )
        self.url = url
        self.table_name = table_name
        self._conn: psycopg.Connection[Any] | None = None
        self._init_db()

    def _get_conn(self) -> psycopg.Connection[Any]:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg_module.connect(self.url)
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_expires
                ON {self.table_name} (expires_at)
            """)
        conn.commit()

    def get(self, key: str) -> Any | None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT value, expires_at FROM {self.table_name} WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        value, expires_at = row
        if datetime.now(UTC) > expires_at:
            self.delete(key)
            return None

        return value

    def set(self, key: str, value: Any, ttl_days: int = 30) -> None:
        conn = self._get_conn()
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=ttl_days)

        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self.table_name} (key, value, expires_at, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    expires_at = EXCLUDED.expires_at
                """,
                (key, json.dumps(value), expires_at, now),
            )
        conn.commit()

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table_name} WHERE key = %s", (key,))
        conn.commit()

    def clear(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table_name}")
        conn.commit()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of deleted rows."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE expires_at < %s",
                (datetime.now(UTC),),
            )
            deleted = cur.rowcount or 0
        conn.commit()
        return deleted

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
