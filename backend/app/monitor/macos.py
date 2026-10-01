"""macOS connection sources.

Two strategies, auto-selected at startup:

* ``PsutilSource`` — used when ``psutil.net_connections()`` works (typically when
  run with sudo). Provides the full system-wide view.
* ``LsofSource``  — non-elevated fallback. Parses ``lsof -nP -i -F pcnT`` and can
  only see the current user's sockets.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess

import psutil

from .base import FAMILY_INET4, FAMILY_INET6, ConnectionSource, RawConnection

_LSOF_TIMEOUT = 8.0

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
        return "UDP" if has_remote else "UDP"
    if tcp_state:
        return tcp_state.upper()
    return "ESTABLISHED" if has_remote else "LISTEN"


class PsutilSource(ConnectionSource):
    name = "psutil"

    def __init__(self) -> None:
        self._name_cache: dict[int, str] = {}

    @property
    def elevated(self) -> bool:
        if os.geteuid() == 0:
            return True
        try:
            for conn in psutil.net_connections(kind="inet"):
                if not conn.pid:
                    continue
                try:
                    if psutil.Process(conn.pid).username() != psutil.Process().username():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except OSError:
            return False
        return False

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


class LsofSource(ConnectionSource):
    """Non-elevated macOS source. Only sees the current user's sockets."""

    name = "lsof"

    def __init__(self) -> None:
        if not shutil.which("lsof"):
            raise RuntimeError("lsof not found — cannot enumerate connections")
        self._euid = os.geteuid()

    @property
    def elevated(self) -> bool:
        return self._euid == 0

    def snapshot(self) -> list[RawConnection]:
        proc = subprocess.run(
            ["lsof", "-nP", "-i", "-F", "pcnTP"],
            capture_output=True,
            text=True,
            timeout=_LSOF_TIMEOUT,
            check=False,
        )
        return parse_lsof_fields(proc.stdout)


def parse_lsof_fields(text: str) -> list[RawConnection]:
    """Parse lsof's machine-readable (``-F``) output.

    Field stream looks like::

        p1339
        cGoogle Chrome Helper
        f28
        PTCP
        n172.16.30.1:50693->142.251.16.188:5228
        TST=ESTABLISHED
    """
    pid = 0
    command = ""
    proto = ""
    addr = ""
    state = ""
    seen: set[str] = set()
    out: list[RawConnection] = []

    def flush() -> None:
        nonlocal addr, state, proto
        if not addr or not pid or not proto:
            addr, state, proto = "", "", ""
            return
        protocol = proto.lower()
        local_token, _, remote_token = addr.partition("->")
        local_ip, local_port = _split_addr(local_token)
        remote_ip, remote_port = ("", 0)
        if remote_token:
            remote_ip, remote_port = _split_addr(remote_token)
        if not local_ip and not remote_ip:
            addr, state, proto = "", "", ""
            return
        status = _status_for(protocol, bool(remote_token), state)
        raw = RawConnection(
            pid=pid,
            process=command or f"pid:{pid}",
            protocol=protocol,
            family=_family_of(local_ip or remote_ip),
            local_ip=local_ip,
            local_port=local_port,
            remote_ip=remote_ip,
            remote_port=remote_port,
            status=status,
        )
        if raw.key not in seen:  # lsof reports dup fds for the same socket
            seen.add(raw.key)
            out.append(raw)
        addr, state, proto = "", "", ""

    for line in text.splitlines():
        if not line:
            continue
        tag, value = line[0], line[1:]
        if tag == "p":
            flush()
            pid = int(value) if value.isdigit() else 0
        elif tag == "c":
            command = value
        elif tag == "P":
            proto = value
        elif tag == "n":
            addr = value
        elif tag.startswith("T") and "=" in line:
            key, _, val = line.partition("=")
            if key == "TST":
                state = val
        elif tag == "f":
            flush()  # new file descriptor → close previous socket entry
    flush()
    return out


def detect_source() -> ConnectionSource:
    """Pick the best available source for this machine/privilege level."""
    try:
        psutil.net_connections(kind="inet")
        return PsutilSource()
    except (OSError, PermissionError, psutil.AccessDenied):
        pass
    return LsofSource()
