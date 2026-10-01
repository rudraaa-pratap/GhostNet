"""Async reverse-DNS resolution with a TTL cache.

Reverse lookups on this machine measured ~0.5s, so they must never run on the
event loop. Every lookup runs in a worker thread with a hard timeout; failures
are cached briefly to avoid hammering the resolver.
"""

from __future__ import annotations

import asyncio
import socket
import time
from concurrent.futures import ThreadPoolExecutor

_SUCCESS_TTL = 3600.0  # 1h — hostnames rarely change for a given IP
_FAIL_TTL = 300.0  # 5min — retry failures later
_TIMEOUT = 1.5


class DnsResolver:
    def __init__(self, max_workers: int = 8) -> None:
        self._cache: dict[str, tuple[str, float]] = {}  # ip -> (hostname, expires_at)
        self._pending: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dns")

    def get_cached(self, ip: str) -> str | None:
        entry = self._cache.get(ip)
        if entry is None:
            return None
        hostname, expires = entry
        if time.monotonic() > expires:
            self._cache.pop(ip, None)
            return None
        return hostname or None

    def resolve_sync(self, ip: str) -> str:
        """Blocking reverse lookup. Safe to call from a worker thread."""
        cached = self.get_cached(ip)
        if cached is not None:
            return cached
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror, OSError):
            hostname = ""
        expires = time.monotonic() + (_SUCCESS_TTL if hostname else _FAIL_TTL)
        self._cache[ip] = (hostname, expires)
        return hostname

    async def resolve(self, ip: str) -> str:
        """Resolve off-loop; returns "" when pending/failed."""
        if not ip or ip in ("0.0.0.0", "::", "*"):
            return ""
        cached = self.get_cached(ip)
        if cached is not None:
            return cached
        if ip in self._pending:
            return ""
        self._pending.add(ip)
        try:
            return await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(self._executor, self.resolve_sync, ip),
                timeout=_TIMEOUT,
            )
        except (TimeoutError, asyncio.TimeoutError):
            return ""
        finally:
            self._pending.discard(ip)

    def cache_size(self) -> int:
        return len(self._cache)
