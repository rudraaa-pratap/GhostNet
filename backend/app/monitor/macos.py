"""macOS connection sources.

Two strategies, auto-selected by :mod:`app.monitor.detect`:

* ``PsutilSource`` (shared, see ``psutil_source.py``) — used when
  ``psutil.net_connections()`` works (typically when run with sudo).
  Provides the full system-wide view.
* ``LsofSource``  — non-elevated fallback. Parses ``lsof -nP -i -F pcnT``
  and can only see the current user's sockets.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import psutil

from .base import ConnectionSource, RawConnection
from .psutil_source import PsutilSource, _family_of, _split_addr, _status_for

__all__ = ["PsutilSource", "LsofSource", "parse_lsof_fields", "detect_source"]

_LSOF_TIMEOUT = 8.0


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
