"""Read endpoints: connections, processes, stats, status, domains, timeline, report."""

from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, Query, Request

from ..monitor.collector import group_by_process
from ..services.aggregation import aggregate_domains

router = APIRouter(prefix="/api", tags=["api"])

_REPORT_WINDOW = 24 * 3600


def _collector(request: Request):
    return request.app.state.collector


def _process_rows(collector) -> list[dict]:
    """Per-application rows with live per-PID bandwidth rolled up."""
    rows = group_by_process(list(collector.connections.values()))
    for row in rows:
        rx = tx = 0.0
        for pid in row["pids"]:
            rate = collector.pid_rates.get(pid)
            if rate:
                rx += rate["rx"]
                tx += rate["tx"]
        row["rx_bps"] = round(rx, 1)
        row["tx_bps"] = round(tx, 1)
    return rows


def _domain_rows(collector) -> list[dict]:
    """Domain groups with live per-connection bandwidth rolled up."""
    groups = aggregate_domains(list(collector.connections.values()))
    for g in groups:
        rx = tx = 0.0
        for conn in collector.connections.values():
            site = conn.registrable or conn.domain
            if site == g["domain"] and (conn.rx_bps or conn.tx_bps):
                rx += conn.rx_bps
                tx += conn.tx_bps
        g["rx_bps"] = round(rx, 1)
        g["tx_bps"] = round(tx, 1)
    return groups


def _matches(
    c: dict,
    *,
    q: str | None,
    protocol: str | None,
    status: str | None,
    app: str | None,
) -> bool:
    if protocol and c["protocol"] != protocol:
        return False
    if status and c["status"].upper() != status.upper():
        return False
    if app and c["process"] != app:
        return False
    if q:
        needle = q.lower()
        haystack = " ".join(
            str(v)
            for v in (
                c["process"],
                c["domain"],
                c["hostname"],
                c["registrable"],
                c["category"],
                c["remote_ip"],
                c["remote_port"],
                c["protocol"],
                c["status"],
            )
        ).lower()
        if needle not in haystack:
            return False
    return True


@router.get("/status")
async def status(request: Request) -> dict:
    c = _collector(request)
    return c.status() | {"ws_clients": request.app.state.manager.client_count}


@router.get("/connections")
async def connections(
    request: Request,
    limit: int = 500,
    q: str | None = None,
    protocol: Literal["tcp", "udp"] | None = None,
    status: str | None = None,
    app: str | None = None,
) -> dict:
    c = _collector(request)
    snapshot = c.snapshot()
    all_conns = snapshot["connections"]
    filtered = [x for x in all_conns if _matches(x, q=q, protocol=protocol, status=status, app=app)]
    filtered.sort(key=lambda x: (x["process"], x["domain"]))
    return {
        "connections": filtered[: max(1, min(limit, 2000))],
        "count": len(filtered),
        "total": len(all_conns),
        "stats": snapshot["stats"],
        "status": snapshot["status"],
        "bandwidth": snapshot["bandwidth"],
    }


@router.get("/processes")
async def processes(request: Request) -> dict:
    rows = _process_rows(_collector(request))
    return {"processes": rows, "count": sum(r["connections"] for r in rows)}


@router.get("/stats")
async def stats(request: Request) -> dict:
    c = _collector(request)
    return {
        "stats": dict(c.stats),
        "history": list(c.history),
        "status": c.status(),
        "bandwidth": c._bandwidth_payload(),
    }


@router.get("/domains")
async def domains(request: Request) -> dict:
    groups = _domain_rows(_collector(request))
    return {"domains": groups, "count": len(groups)}


@router.get("/timeline")
async def timeline(
    request: Request,
    since: float | None = None,
    until: float | None = None,
    limit: int = Query(default=5000, le=20000),
    kind: Literal["open", "close"] | None = None,
) -> dict:
    c = _collector(request)
    store = c.store
    if store is None:
        return {"events": [], "count": 0, "stored": 0}
    if since is None and until is None:
        since = time.time() - 3600  # default: last hour
    events = store.query(since=since, until=until, limit=limit, kind=kind)
    return {"events": events, "count": len(events), "stored": store.count()}


@router.get("/alerts")
async def alerts(request: Request, limit: int = Query(default=100, le=1000)) -> dict:
    """First-seen application → destination alerts (PDF §8 V3: "alerts")."""
    c = _collector(request)
    store = c.store
    if store is None:
        return {"alerts": c.alerts, "count": len(c.alerts), "total": len(c.alerts)}
    rows = store.recent_alerts(limit)
    return {"alerts": rows, "count": len(rows), "total": store.alert_count()}


@router.get("/report")
async def report(
    request: Request,
    window: int = Query(default=_REPORT_WINDOW, le=7 * 24 * 3600),
) -> dict:
    """Point-in-time snapshot used by the printable export (PDF §8 V3: "export")."""
    c = _collector(request)
    now = time.time()
    store = c.store
    events = store.query(since=now - window, limit=20000) if store is not None else []

    opens = sum(1 for e in events if e["kind"] == "open")
    closes = len(events) - opens
    buckets: dict[int, dict] = {}
    for e in events:
        hour = int(e["ts"] // 3600)
        b = buckets.setdefault(hour, {"hour": hour * 3600, "opens": 0, "closes": 0})
        if e["kind"] == "open":
            b["opens"] += 1
        else:
            b["closes"] += 1
    hourly = sorted(buckets.values(), key=lambda b: b["hour"])

    return {
        "generated_at": now,
        "window": window,
        "status": c.status(),
        "stats": dict(c.stats),
        "processes": _process_rows(c),
        "domains": _domain_rows(c),
        "connections": [c2.to_dict() for c2 in c.connections.values()],
        "timeline": {
            "events": len(events),
            "opens": opens,
            "closes": closes,
            "hourly": hourly,
            "stored": store.count() if store is not None else 0,
        },
        "alerts": list(c.alerts),
    }
