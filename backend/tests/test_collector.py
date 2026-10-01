"""Collector diffing / event emission tests with a scripted source."""

import asyncio

import pytest

from app.monitor.base import ConnectionSource, RawConnection
from app.monitor.collector import NetworkCollector, group_by_process
from app.services.dns import DnsResolver


class FakeSource(ConnectionSource):
    name = "fake"

    def __init__(self):
        self.queue: list[list[RawConnection]] = []
        self.current: list[RawConnection] = []

    @property
    def elevated(self) -> bool:
        return False

    def snapshot(self) -> list[RawConnection]:
        if self.queue:
            self.current = self.queue.pop(0)
        return list(self.current)


def conn(pid=1, proc="Chrome", rip="142.250.196.110", rport=443, hint="") -> RawConnection:
    return RawConnection(
        pid=pid,
        process=proc,
        protocol="tcp",
        family="inet4",
        local_ip="192.168.1.24",
        local_port=50000 + pid,
        remote_ip=rip,
        remote_port=rport,
        status="ESTABLISHED",
        hostname_hint=hint,
    )


def run(coro):
    return asyncio.run(coro)


def test_open_close_diff_events():
    src = FakeSource()
    src.queue = [[conn()], [conn(), conn(pid=2, proc="Code", rip="140.82.113.4")], []]
    collector = NetworkCollector(source=src, resolver=DnsResolver(), poll_interval=0.01)

    async def go():
        e1 = await collector.poll_once()
        e2 = await collector.poll_once()
        e3 = await collector.poll_once()
        return e1, e2, e3

    e1, e2, e3 = run(go())
    opens1 = [e for e in e1 if e["type"] == "conn_open"]
    assert len(opens1) == 1
    assert opens1[0]["connection"]["process"] == "Chrome"
    assert opens1[0]["connection"]["domain"] == "142.250.196.110"

    opens2 = [e for e in e2 if e["type"] == "conn_open"]
    closes2 = [e for e in e2 if e["type"] == "conn_close"]
    assert len(opens2) == 1 and opens2[0]["connection"]["process"] == "Code"
    assert closes2 == []

    closes3 = [e for e in e3 if e["type"] == "conn_close"]
    assert len(closes3) == 2
    assert collector.connections == {}
    assert collector.total_requests == 2


def test_hostname_hint_skips_dns():
    src = FakeSource()
    src.queue = [[conn(hint="google.com")]]
    collector = NetworkCollector(source=src, resolver=DnsResolver())

    events = run(collector.poll_once())
    opened = next(e for e in events if e["type"] == "conn_open")
    assert opened["connection"]["hostname"] == "google.com"
    assert opened["connection"]["domain"] == "google.com"


def test_stats_event_and_counts():
    src = FakeSource()
    src.queue = [[conn(), conn(pid=2, proc="Code")], [conn()]]
    collector = NetworkCollector(source=src, resolver=DnsResolver())

    async def go():
        await collector.poll_once()
        e2 = await collector.poll_once()
        return e2

    events = run(go())
    stats_event = next(e for e in events if e["type"] == "stats")
    stats = stats_event["stats"]
    assert stats["connections"] == 1
    assert stats["applications"] == 1
    assert stats["requests"] == 2


def test_group_by_process():
    src = FakeSource()
    src.queue = [[conn(), conn(pid=1, rip="142.250.196.206"), conn(pid=2, proc="Code")]]
    collector = NetworkCollector(source=src, resolver=DnsResolver())
    run(collector.poll_once())
    rows = group_by_process(list(collector.connections.values()))
    assert rows[0]["process"] == "Chrome"
    assert rows[0]["connections"] == 2
    assert rows[0]["pids"] == [1]
    assert len(rows) == 2


def test_collector_status():
    src = FakeSource()
    collector = NetworkCollector(source=src, resolver=DnsResolver())
    status = collector.status()
    assert status["source"] == "fake"
    assert status["elevated"] is False
    assert status["demo"] is False


@pytest.mark.parametrize("count", [0, 5])
def test_snapshot_shape(count):
    src = FakeSource()
    if count:
        src.queue = [list(range(count)) and [conn(pid=i) for i in range(count)]]
    collector = NetworkCollector(source=src, resolver=DnsResolver())
    if count:
        run(collector.poll_once())
    snap = collector.snapshot()
    assert set(snap) == {"connections", "stats", "status", "bandwidth"}
    assert len(snap["connections"]) == count
