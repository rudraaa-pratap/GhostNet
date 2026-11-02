"""Cross-platform psutil-based connection source.

``psutil.net_connections()`` exists on macOS, Linux and Windows, but the
privilege rules differ:

* posix (macOS/Linux) — unprivileged calls raise or silently omit other
  users' sockets; the full system-wide view needs root.
* windows — the call always succeeds, but connections owned by other users
  (and system services) come back with ``pid=None``; the full view needs
  Administrator.

Everything else above this file is platform-agnostic, so every OS source
shares this one implementation and only overrides elevation detection.
"""

from __future__ import annotations

import os
import re
import socket

import psutil

from .base import FAMILY_INET4, FAMILY_INET6, ConnectionSource, RawConnection

_ADDR_RE = re.compile(r"^(?P<ip>.+):(?P<port>\d+)$")
_IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")


def _split_addr(token: str) -> tuple[str, int]:
    """Split ``1.2.3.4:443`` / ``[::1]:443`` / ``*:80`` into (ip, port)."""
    if token.startswith("["):  # bracketed IPv6: [::1]:443
        host, _, port = token[1:].partition("]:")
        return host, int(port) if port.isdigit() else 0
    m = _ADDR_RE.match(token)
    if not m:
        return token, 0
    return m.group("ip"), int(m.group("port"))


def _family_of(ip: str) -> str:
    return FAMILY_INET6 if ":" in ip and _IPV6_RE.match(ip) else FAMILY_INET4


def _status_for(protocol: str, has_remote: bool, tcp_state: str) -> str:
    if protocol == "udp":
        return "UDP"
    if tcp_state:
        return tcp_state.upper()
    return "ESTABLISHED" if has_remote else "LISTEN"


def is_admin() -> bool:
    """Elevation check that works on posix (root) and Windows (Administrator)."""
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError, ImportError):
        return False


class PsutilSource(ConnectionSource):
    name = "psutil"

    def __init__(self) -> None:
        self._name_cache: dict[int, str] = {}

    def _sees_other_users(self) -> bool:
        """True when the connection list exposes another user's process."""
        try:
            me = psutil.Process().username()
            for conn in psutil.net_connections(kind="inet"):
                if not conn.pid:
                    continue
                try:
                    if psutil.Process(conn.pid).username() != me:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (OSError, psutil.AccessDenied):
            return False
        return False

    @property
    def elevated(self) -> bool:
        if is_admin():
            return True
        return self._sees_other_users()

    def _process_name(self, pid: int) -> str:
        cached = self._name_cache.get(pid)
        if cached is not None:
            return cached
        try:
            name = psutil.Process(pid).name() or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            name = ""
        if len(self._name_cache) > 4096:
            self._name_cache.clear()
        self._name_cache[pid] = name
        return name

    def snapshot(self) -> list[RawConnection]:
        out: list[RawConnection] = []
        for c in psutil.net_connections(kind="inet"):
            if c.pid is None:
                continue
            protocol = "tcp" if c.type == socket.SOCK_STREAM else "udp"
            l_ip, l_port = (c.laddr.ip, c.laddr.port) if c.laddr else ("", 0)
            r_ip, r_port = (c.raddr.ip, c.raddr.port) if c.raddr else ("", 0)
            if not l_ip and not r_ip:
                continue
            status = _status_for(protocol, bool(r_ip), c.status or "")
            out.append(
                RawConnection(
                    pid=c.pid,
                    process=self._process_name(c.pid),
                    protocol=protocol,
                    family=_family_of(l_ip or r_ip),
                    local_ip=l_ip,
                    local_port=l_port,
                    remote_ip=r_ip,
                    remote_port=r_port,
                    status=status,
                )
            )
        return out
