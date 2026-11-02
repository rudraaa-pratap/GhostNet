"""Platform dispatch + the shared cross-platform psutil source.

The mocks imitate ``psutil.net_connections()`` rows so every assertion runs
on every OS (no live-socket requirements), which is exactly what lets the
Windows code path be exercised from macOS and CI.
"""

import socket
from collections import namedtuple
from types import SimpleNamespace

import psutil
import pytest

from app.monitor.base import ConnectionSource
from app.monitor.detect import detect_source
from app.monitor.linux import LinuxSource
from app.monitor.linux import detect_source as linux_detect
from app.monitor.psutil_source import PsutilSource, is_admin
from app.monitor.windows import WindowsSource
from app.monitor.windows import detect_source as windows_detect

_Endpoint = namedtuple("_Endpoint", ["ip", "port"])

_ESTABLISHED_TCP = [
    dict(pid=4832, status="ESTABLISHED"),
    dict(pid=4832, type=socket.SOCK_DGRAM, raddr=None, status="NONE"),
    dict(pid=None),  # other users / system — skipped
    dict(pid=701, laddr=None, raddr=None),  # no endpoints — skipped
    dict(pid=701, laddr=_Endpoint("::1", 27017), raddr=None, status="LISTEN"),
]


def _entries(**overrides) -> list[SimpleNamespace]:
    """Build one mocked psutil.net_connections() result set."""
    rows = []
    for spec in _ESTABLISHED_TCP:
        row = {
            "type": socket.SOCK_STREAM,
            "laddr": _Endpoint("172.16.30.1", 50693),
            "raddr": _Endpoint("142.251.16.188", 443),
            **spec,
            **overrides,
        }
        rows.append(SimpleNamespace(**row))
    return rows


class _FakeProcess:
    def __init__(self, name: str = "chrome", user: str = "me") -> None:
        self._name = name
        self._user = user

    def name(self) -> str:
        return self._name

    def username(self) -> str:
        return self._user


def _fake_psutil(monkeypatch, rows, process_user: str = "me") -> None:
    monkeypatch.setattr(psutil, "net_connections", lambda kind="inet": rows)
    monkeypatch.setattr(psutil, "Process", lambda pid=None: _FakeProcess("chrome", process_user))


def test_snapshot_maps_psutil_entries(monkeypatch):
    _fake_psutil(monkeypatch, _entries())
    raws = PsutilSource().snapshot()
    assert len(raws) == 3  # pid=None row and endpoint-less row are skipped

    tcp = raws[0]
    assert tcp.pid == 4832
    assert tcp.process == "chrome"
    assert tcp.protocol == "tcp"
    assert tcp.family == "inet4"
    assert (tcp.local_ip, tcp.local_port) == ("172.16.30.1", 50693)
    assert (tcp.remote_ip, tcp.remote_port) == ("142.251.16.188", 443)
    assert tcp.status == "ESTABLISHED"

    udp = raws[1]  # datagram socket → no remote attr, labeled UDP
    assert udp.protocol == "udp"
    assert udp.remote_ip == ""
    assert udp.status == "UDP"

    v6 = raws[2]  # IPv6-only local endpoint
    assert v6.family == "inet6"
    assert v6.status == "LISTEN"


def test_snapshot_falls_back_to_tcp_state_for_empty_status(monkeypatch):
    _fake_psutil(monkeypatch, _entries(raddr=None, status=""))
    raws = PsutilSource().snapshot()
    assert {r.status for r in raws} == {"UDP", "LISTEN"}  # no remote → not ESTABLISHED


def test_elevated_true_for_admin(monkeypatch):
    _fake_psutil(monkeypatch, [])
    monkeypatch.setattr("app.monitor.psutil_source.is_admin", lambda: True)
    assert PsutilSource().elevated is True


def test_elevated_true_when_foreign_process_visible(monkeypatch):
    _fake_psutil(monkeypatch, _entries(pid=999))

    def fake_process(pid=None) -> _FakeProcess:
        user = "me" if pid is None else "someone-else"
        return _FakeProcess("svc", user=user)

    monkeypatch.setattr(psutil, "Process", fake_process)
    assert PsutilSource().elevated is True


def test_elevated_false_when_access_denied(monkeypatch):
    def denied(kind="inet"):
        raise psutil.AccessDenied(pid=1)

    monkeypatch.setattr(psutil, "net_connections", denied)
    assert PsutilSource().elevated is False


def test_is_admin_returns_bool():
    assert isinstance(is_admin(), bool)


def test_name_cache_is_reused(monkeypatch):
    calls = {"count": 0}

    def process(pid=None):
        calls["count"] += 1
        return _FakeProcess("chrome")

    _fake_psutil(monkeypatch, _entries())
    monkeypatch.setattr(psutil, "Process", process)
    src = PsutilSource()
    raws_first = src.snapshot()
    assert calls["count"] == 2  # two distinct pids
    src.snapshot()
    raws_second = src.snapshot()
    assert calls["count"] == 2  # cache hit → no new Process() calls
    assert [r.key for r in raws_first] == [r.key for r in raws_second]


def test_platform_modules_share_the_implementation():
    # Same class object → identical snapshot/path everywhere.
    assert WindowsSource is PsutilSource
    assert LinuxSource is PsutilSource


def test_windows_detect_never_needs_a_fallback():
    assert windows_detect().name == "psutil"


def test_linux_detect_surfaces_actionable_error_when_psutil_denied(monkeypatch):
    def boom(kind="inet"):
        raise psutil.AccessDenied(pid=1)

    monkeypatch.setattr(psutil, "net_connections", boom)
    with pytest.raises(RuntimeError, match="sudo"):
        linux_detect()


def test_detect_dispatch_returns_a_connection_source():
    source = detect_source()
    assert isinstance(source, ConnectionSource)
