"""The collection loop: poll OS sockets → diff → enrich → emit events.

Data flow (PDF §6):
  OS reports connection → map PID → process → reverse-DNS the remote IP →
  normalize event (Chrome → TCP → google.com:443) → emit over WebSocket.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable

import psutil

from ..services.aggregation import categorize, registrable_domain
from ..services.alerts import AlertWatcher
from ..services.dns import DnsResolver
from ..services.history import EventStore
from .bandwidth import BandwidthSampler, demo_rates
from .base import Connection, ConnectionSource, RawConnection

log = logging.getLogger("ghostnet.collector")

EmitFn = Callable[[dict], Awaitable[None]]

_HISTORY_LEN = 1200  # ~30 min of speed samples at 1.5s


class NetworkCollector:
    def __init__(
        self,
        source: ConnectionSource,
        resolver: DnsResolver | None = None,
        emit: EmitFn | None = None,
        poll_interval: float = 1.5,
        demo: bool = False,
        store: EventStore | None = None,
        sample_bandwidth: bool = True,
    ) -> None:
        self.source = source
        self.resolver = resolver or DnsResolver()
        self._emit = emit
        self.poll_interval = poll_interval
        self.demo = demo
        self.store = store
        self.bandwidth = BandwidthSampler(enabled=sample_bandwidth and not demo)
        self.alert_watcher = AlertWatcher(store)

        self.connections: dict[str, Connection] = {}
        self.started_at = time.time()
        self.total_requests = 0  # cumulative connection-open count ("REQUESTS")
        self.pid_rates: dict[int, dict] = {}
        self._last_prune = time.time()

        self.stats: dict = {
            "download_bps": 0.0,
            "upload_bps": 0.0,
            "total_recv": 0,
            "total_sent": 0,
            "connections": 0,
            "established": 0,
            "applications": 0,
            "domains": 0,
            "requests": 0,
        }
        self.history: deque[dict] = deque(maxlen=_HISTORY_LEN)

        self._io_prev: tuple[float, int, int] | None = None
        self._demo_bytes = (1_250_000.0, 180_000.0)  # fake down/up bytes
        self._resolving: set[str] = set()
        self._tasks: set[asyncio.Task] = set()
        self._running = False

    # ------------------------------------------------------------------ state

    def snapshot(self) -> dict:
        return {
            "connections": [c.to_dict() for c in self.connections.values()],
            "stats": dict(self.stats),
            "status": self.status(),
            "bandwidth": self._bandwidth_payload(),
        }

    def _bandwidth_payload(self) -> dict:
        return {
            "rates": {str(pid): r for pid, r in self.pid_rates.items()},
            "connections": {
                c.conn_id: {"rx": c.rx_bps, "tx": c.tx_bps}
                for c in self.connections.values()
                if c.rx_bps or c.tx_bps
            },
        }

    @property
    def alerts(self) -> list[dict]:
        """Recent first-seen application → destination alerts (newest first)."""
        return self.alert_watcher.recent

    def status(self) -> dict:
        return {
            "source": self.source.name,
            "elevated": self.source.elevated,
            "demo": self.demo,
            "uptime": round(time.time() - self.started_at, 1),
            "poll_interval": self.poll_interval,
            "total_requests": self.total_requests,
            "bandwidth": "nettop" if self.bandwidth.enabled else ("demo" if self.demo else "off"),
        }

    # ------------------------------------------------------------------- poll

    async def poll_once(self) -> list[dict]:
        """One full sample: diff connections, refresh stats, sample bandwidth."""
        raws = await asyncio.to_thread(self.source.snapshot)
        events: list[dict] = []
        now = time.time()
        seen_keys: set[str] = set()

        for raw in raws:
            seen_keys.add(raw.key)
            existing = self.connections.get(raw.key)
            if existing is not None:
                existing.last_seen = now
                if existing.status != raw.status:
                    existing.status = raw.status
                    events.append(
                        {"type": "conn_update", "ts": now, "connection": existing.to_dict()}
                    )
                continue
            conn = Connection.from_raw(raw)
            self._enrich(conn)
            self.connections[raw.key] = conn
            self.total_requests += 1
            events.append({"type": "conn_open", "ts": now, "connection": conn.to_dict()})
            self._schedule_resolve(conn.remote_ip)

        for key in [k for k in self.connections if k not in seen_keys]:
            gone = self.connections.pop(key)
            events.append({"type": "conn_close", "ts": now, "connection": gone.to_dict()})

        self._refresh_stats(now)
        events.append({"type": "stats", "ts": now, "stats": dict(self.stats)})
        events.append({"type": "bandwidth", "ts": now, **await self._sample_bandwidth(now)})

        fresh_alerts = self.alert_watcher.check(list(self.connections.values()))
        if fresh_alerts:
            events.append({"type": "alert", "ts": now, "alerts": fresh_alerts})
        return events

    @staticmethod
    def _enrich(conn: Connection) -> None:
        """Attach registrable domain + category once a hostname is known."""
        if conn.hostname:
            conn.registrable = registrable_domain(conn.hostname)
            conn.category = categorize(conn.hostname)
        elif conn.remote_ip:
            conn.category = "Pending"
        else:
            conn.category = "Local"

    async def _sample_bandwidth(self, now: float) -> dict:
        """Per-process (nettop) + per-connection rates; demo synthesizes them."""
        if self.demo:
            pid_rates, conn_rates = demo_rates(list(self.connections.values()), now)
        else:
            pid_rates, conn_rates = await asyncio.to_thread(self.bandwidth.sample)

        self.pid_rates = pid_rates
        index = {
            (c.protocol, c.remote_ip, c.remote_port, c.local_port): c
            for c in self.connections.values()
        }
        active: dict[str, dict] = {}
        for c in self.connections.values():
            c.rx_bps = c.tx_bps = 0.0
        for key, rate in conn_rates.items():
            conn = index.get(key)
            if conn is None:
                continue
            conn.rx_bps = rate["rx"]
            conn.tx_bps = rate["tx"]
            if rate["rx"] >= 1 or rate["tx"] >= 1:
                active[conn.conn_id] = rate
        return {
            "rates": {str(pid): r for pid, r in list(pid_rates.items())[:150]},
            "connections": active,
        }

    def _schedule_resolve(self, ip: str) -> None:
        if not ip or ip in self._resolving or self.resolver.get_cached(ip) is not None:
            return
        self._resolving.add(ip)
        task = asyncio.create_task(self._resolve(ip))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _resolve(self, ip: str) -> None:
        try:
            hostname = await self.resolver.resolve(ip)
        finally:
            self._resolving.discard(ip)
        if not hostname:
            return
        site = registrable_domain(hostname)
        category = categorize(hostname)
        updated = False
        for conn in self.connections.values():
            if conn.remote_ip == ip and not conn.hostname:
                conn.hostname = hostname
                conn.registrable = site
                conn.category = category
                updated = True
        if updated and self._emit:
            await self._emit(
                {
                    "type": "dns",
                    "ip": ip,
                    "hostname": hostname,
                    "registrable": site,
                    "category": category,
                }
            )

    # ------------------------------------------------------------------ stats

    def _refresh_stats(self, now: float) -> None:
        if self.demo:
            down, up = self._demo_walk(now)
            total_recv = int(self.stats["total_recv"] + down * self.poll_interval)
            total_sent = int(self.stats["total_sent"] + up * self.poll_interval)
        else:
            io = psutil.net_io_counters()
            down = up = 0.0
            if self._io_prev is not None:
                dt = max(now - self._io_prev[0], 1e-6)
                down = max(0.0, (io.bytes_recv - self._io_prev[1]) / dt)
                up = max(0.0, (io.bytes_sent - self._io_prev[2]) / dt)
            self._io_prev = (now, io.bytes_recv, io.bytes_sent)
            total_recv, total_sent = io.bytes_recv, io.bytes_sent

        conns = list(self.connections.values())
        self.stats = {
            "download_bps": round(down, 1),
            "upload_bps": round(up, 1),
            "total_recv": total_recv,
            "total_sent": total_sent,
            "connections": len(conns),
            "established": sum(1 for c in conns if c.status == "ESTABLISHED"),
            "applications": len({c.process for c in conns}),
            "domains": len({c.domain for c in conns if c.remote_ip}),
            "requests": self.total_requests,
        }
        self.history.append({"t": now, "down": round(down, 1), "up": round(up, 1)})

    @staticmethod
    def _demo_walk(now: float) -> tuple[float, float]:
        """Smooth-ish random walk so demo bandwidth looks alive."""
        import math

        base = 2_400_000 + 1_600_000 * math.sin(now / 7) + 400_000 * math.sin(now * 1.7)
        up = max(40_000.0, base * 0.12 + 60_000 * math.sin(now * 2.3))
        return max(80_000.0, base), up

    # ------------------------------------------------------------------- loop

    async def run(self) -> None:
        if self._running:
            return
        self._running = True
        log.info("collector started (source=%s, demo=%s)", self.source.name, self.demo)
        while self._running:
            try:
                events = await self.poll_once()
                self._persist(events)
                if self._emit:
                    for event in events:
                        await self._emit(event)
                if time.time() - self._last_prune > 3600 and self.store is not None:
                    await asyncio.to_thread(self.store.prune)
                    self._last_prune = time.time()
            except Exception:
                log.exception("poll failed")
            await asyncio.sleep(self.poll_interval)

    def _persist(self, events: list[dict]) -> None:
        """Write open/close events to SQLite for the request timeline."""
        if self.store is None:
            return
        batch = [timeline_entry(e) for e in events if e["type"] in ("conn_open", "conn_close")]
        if not batch:
            return
        try:
            self.store.insert_events(batch)
        except Exception:
            log.exception("timeline write failed")

    def stop(self) -> None:
        self._running = False
        for task in list(self._tasks):
            task.cancel()

    async def emit(self, event: dict) -> None:
        if self._emit:
            await self._emit(event)


def group_by_process(connections: list[Connection]) -> list[dict]:
    """Aggregate connection records into per-application rows."""
    apps: dict[str, dict] = {}
    for c in connections:
        row = apps.setdefault(
            c.process,
            {
                "process": c.process,
                "pids": set(),
                "connections": 0,
                "established": 0,
                "domains": set(),
                "protocols": set(),
            },
        )
        row["pids"].add(c.pid)
        row["connections"] += 1
        if c.status == "ESTABLISHED":
            row["established"] += 1
        if c.remote_ip:
            row["domains"].add(c.domain)
        row["protocols"].add(c.protocol)
    out = []
    for row in apps.values():
        row["pids"] = sorted(row["pids"])
        row["domains"] = sorted(row["domains"])
        row["protocols"] = sorted(row["protocols"])
        out.append(row)
    out.sort(key=lambda r: r["connections"], reverse=True)
    return out


def timeline_entry(event: dict) -> dict:
    """Map a conn_open/conn_close WS event to a timeline DB row."""
    c = event["connection"]
    return {
        "ts": event.get("ts", time.time()),
        "kind": "open" if event["type"] == "conn_open" else "close",
        "process": c.get("process"),
        "pid": c.get("pid"),
        "protocol": c.get("protocol"),
        "local_port": c.get("local_port"),
        "remote_ip": c.get("remote_ip"),
        "remote_port": c.get("remote_port"),
        "domain": c.get("domain"),
        "registrable": c.get("registrable"),
        "category": c.get("category"),
        "opened_at": c.get("opened_at"),
    }


__all__ = ["NetworkCollector", "group_by_process", "timeline_entry", "RawConnection"]
