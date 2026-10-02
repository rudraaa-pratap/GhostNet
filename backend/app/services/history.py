"""SQLite-backed connection event history for the request timeline.

Local-first: the database lives on disk next to the backend and is pruned to
24 hours of events (PDF §8 V3: "24-hour history").
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from pathlib import Path

_RETENTION_SECONDS = 24 * 3600

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    process TEXT,
    pid INTEGER,
    protocol TEXT,
    local_port INTEGER,
    remote_ip TEXT,
    remote_port INTEGER,
    domain TEXT,
    registrable TEXT,
    category TEXT,
    opened_at REAL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS seen (
    key TEXT PRIMARY KEY,
    first_seen REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    process TEXT NOT NULL,
    site TEXT NOT NULL,
    category TEXT,
    ip TEXT,
    port INTEGER
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_COLUMNS = (
    "ts",
    "kind",
    "process",
    "pid",
    "protocol",
    "local_port",
    "remote_ip",
    "remote_port",
    "domain",
    "registrable",
    "category",
    "opened_at",
)


def default_db_path() -> Path:
    env = os.environ.get("GHOSTNET_DB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data" / "ghostnet.db"


class EventStore:
    """Thread-safe thin wrapper over a SQLite connection."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)
        self.prune()

    def insert_events(self, events: list[dict]) -> int:
        """Persist timeline events (dicts with ts/kind/... keys). Returns count."""
        if not events:
            return 0
        rows = [tuple(e.get(col) for col in _COLUMNS) for e in events]
        placeholders = ",".join("?" * len(_COLUMNS))
        with self._lock, self._conn:
            self._conn.executemany(
                f"INSERT INTO events ({','.join(_COLUMNS)}) VALUES ({placeholders})",
                rows,
            )
        return len(rows)

    def query(
        self,
        since: float | None = None,
        until: float | None = None,
        limit: int = 2000,
        kind: str | None = None,
    ) -> list[dict]:
        sql = f"SELECT {','.join(_COLUMNS)} FROM events"
        clauses: list[str] = []
        params: list = []
        if since is not None:
            clauses.append("ts >= ?")
            params.append(since)
        if until is not None:
            clauses.append("ts <= ?")
            params.append(until)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(max(1, min(int(limit), 20000)))
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in reversed(rows)]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def prune(self, retention: float = _RETENTION_SECONDS) -> int:
        cutoff = time.time() - retention
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            return cur.rowcount

    # ------------------------------------------------------------- alerts

    def get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else row["value"]

    def set_meta(self, key: str, value: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def mark_seen(self, keys: list[str]) -> list[str]:
        """Record keys as known; return only those that were unknown."""
        if not keys:
            return []
        now = time.time()
        fresh: list[str] = []
        with self._lock, self._conn:
            for key in keys:
                cur = self._conn.execute(
                    "INSERT OR IGNORE INTO seen (key, first_seen) VALUES (?, ?)",
                    (key, now),
                )
                if cur.rowcount:
                    fresh.append(key)
        return fresh

    def insert_alerts(self, rows: list[dict]) -> list[dict]:
        """Persist alert rows, returning them with their generated ids."""
        out: list[dict] = []
        with self._lock, self._conn:
            for row in rows:
                ts = row.get("ts") or time.time()
                cur = self._conn.execute(
                    "INSERT INTO alerts (ts, process, site, category, ip, port) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        ts,
                        row["process"],
                        row["site"],
                        row.get("category"),
                        row.get("ip"),
                        row.get("port"),
                    ),
                )
                out.append({**row, "id": cur.lastrowid, "ts": ts})
        return out

    def recent_alerts(self, limit: int = 100) -> list[dict]:
        """Newest-first alert history."""
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, ts, process, site, category, ip, port FROM alerts "
                "ORDER BY ts DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def alert_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
