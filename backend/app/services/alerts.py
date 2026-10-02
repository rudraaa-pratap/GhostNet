"""First-seen application → destination alerts (PDF §8 V3: "alerts").

Local-first: the baseline of already-known destinations lives in the same
SQLite file as the timeline, so restarting GhostNet never re-fires old alerts.
"""

from __future__ import annotations

import time

from ..monitor.base import Connection
from .history import EventStore

_BOOTSTRAP_KEY = "alerts_bootstrapped"
_RETAINED = 200


def destination_key(conn: Connection) -> tuple[str, str] | None:
    """Identify an app→site pair, or None when there is no remote endpoint."""
    if not conn.remote_ip:
        return None
    site = conn.registrable or conn.domain
    if not site:
        return None
    return conn.process, site


class AlertWatcher:
    """Emit an alert the first time an application talks to a destination.

    The very first observation seeds the baseline silently, and a short warm-up
    window swallows the churn an app makes while it starts up — so restarting
    GhostNet never re-fires alerts for traffic that was already there.
    """

    def __init__(self, store: EventStore | None = None, warmup_seconds: float = 60.0) -> None:
        self.store = store
        self.warmup_seconds = max(0.0, warmup_seconds)
        self.recent: list[dict] = list(store.recent_alerts(_RETAINED)) if store else []
        self._memory_seen: set[str] = set()
        self._bootstrapped = store is None and bool(self.recent)
        self._started = time.time()

    def _candidates(self, connections: list[Connection]) -> dict[str, dict]:
        found: dict[str, dict] = {}
        detected_at = time.time()
        for conn in connections:
            parts = destination_key(conn)
            if parts is None:
                continue
            process, site = parts
            key = f"{process}|{site}"
            found.setdefault(
                key,
                {
                    "ts": detected_at,
                    "process": process,
                    "site": site,
                    "category": conn.category or "Other",
                    "ip": conn.remote_ip,
                    "port": conn.remote_port,
                },
            )
        return found

    def check(self, connections: list[Connection]) -> list[dict]:
        """Compare current traffic against the known baseline; return new alerts."""
        candidates = self._candidates(connections)
        if not candidates:
            return []

        in_warmup = time.time() - self._started < self.warmup_seconds

        if self.store is not None:
            bootstrapped = self.store.get_meta(_BOOTSTRAP_KEY) == "1"
            fresh_keys = self.store.mark_seen(list(candidates))
            if not bootstrapped:
                self.store.set_meta(_BOOTSTRAP_KEY, "1")
                return []
            if in_warmup:
                return []
            rows = [candidates[k] for k in fresh_keys]
            if rows:
                rows = self.store.insert_alerts(rows)
        else:
            bootstrapped = self._bootstrapped
            fresh_keys = [k for k in candidates if k not in self._memory_seen]
            self._memory_seen.update(candidates)
            if not bootstrapped:
                self._bootstrapped = True
                return []
            if in_warmup:
                return []
            rows = [candidates[k] for k in fresh_keys]

        if not rows:
            return []
        self.recent = rows + self.recent
        del self.recent[_RETAINED:]
        return rows


def _now() -> float:
    import time

    return time.time()


__all__ = ["AlertWatcher", "destination_key"]
