"""Per-process / per-connection bandwidth sampling via macOS ``nettop``.

Why nettop: ``psutil.Process.io_counters()`` does not exist on macOS, and the
OS exposes no per-connection byte counters elsewhere without packet capture.
``nettop`` works unprivileged, system-wide, and a one-shot sample costs ~20ms.

Sample line types (``nettop -L 1 -x``)::

    process: 02:33:11.194107,apsd.365,,,5408,11554,0,0,0,,,,,,,,,,,,
    conn:    02:34:20.185318,tcp4 172.16.30.1:50421<->17.57.147.5:5223,
             utun4,Established,5408,11594,...
"""

from __future__ import annotations

import math
import shutil
import subprocess
import time

from .base import Connection

_NETTOP_TIMEOUT = 6.0
_MIN_RATE = 100.0  # ignore <100 B/s noise


def _to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _split_endpoint(token: str) -> tuple[str, int]:
    """``1.2.3.4:443`` / ``*:5000`` / ``*.55294`` / ``[::1]:443`` / ``fe80::1%en0:80``."""
    if token.startswith("["):
        host, _, port = token[1:].partition("]:")
        return host.split("%", 1)[0], int(port) if port.isdigit() else 0
    if ":" in token:
        host, _, port = token.rpartition(":")
        if port.isdigit():
            return host.split("%", 1)[0], int(port)
        if host == "*":
            return "*", 0
    if "." in token:
        host, _, port = token.rpartition(".")
        if port.isdigit():
            return host, int(port)
        if host == "*":
            return "*", 0
    return token.split("%", 1)[0], 0


def parse_nettop(text: str) -> tuple[dict[int, tuple[int, int]], dict[tuple, tuple[int, int]]]:
    """Parse one nettop sample.

    Returns ``(pid_rates_bytes, conn_rates_bytes)`` where keys are
    ``pid`` and ``(protocol, remote_ip, remote_port, local_port)``.
    """
    pids: dict[int, tuple[int, int]] = {}
    conns: dict[tuple, tuple[int, int]] = {}
    for line in text.splitlines():
        if not line or line.startswith("time,"):
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        label = parts[1]
        if not label:
            continue
        rx, tx = _to_int(parts[4]), _to_int(parts[5])
        if "<->" in label:
            proto = "tcp" if label.startswith("tcp") else "udp"
            endpoints = label.split(" ", 1)[-1]
            local_token, _, remote_token = endpoints.partition("<->")
            remote_ip, remote_port = _split_endpoint(remote_token)
            if remote_ip in ("", "*"):
                continue  # unconnected socket — no remote attribution
            _, local_port = _split_endpoint(local_token)
            key = (proto, remote_ip.rstrip("."), remote_port, local_port)
            conns[key] = (rx, tx)
        else:
            name, dot, pid_s = label.rpartition(".")
            if not dot or not pid_s.isdigit():
                continue
            pids[int(pid_s)] = (rx, tx)
    return pids, conns


class BandwidthSampler:
    """Tracks byte counters across samples and derives rates (bytes/sec)."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and shutil.which("nettop") is not None
        self._pid_prev: dict[int, tuple[float, int, int]] = {}
        self._conn_prev: dict[tuple, tuple[float, int, int]] = {}
        self.pid_rates: dict[int, dict] = {}
        self.conn_rates: dict[tuple, dict] = {}
        self.last_error: str | None = None

    def sample(self) -> tuple[dict[int, dict], dict[tuple, dict]]:
        """Take a sample; returns (pid_rates, conn_rates) as {rx, tx} B/s."""
        if not self.enabled:
            return {}, {}
        now = time.time()
        try:
            proc = subprocess.run(
                ["nettop", "-L", "1", "-x"],
                capture_output=True,
                text=True,
                timeout=_NETTOP_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.last_error = str(exc)
            return self.pid_rates, self.conn_rates

        pids, conns = parse_nettop(proc.stdout)
        self.pid_rates = self._diff(pids, self._pid_prev, now, key_type=int)
        self.conn_rates = self._diff(conns, self._conn_prev, now, key_type=tuple)
        return self.pid_rates, self.conn_rates

    @staticmethod
    def _diff(current, prev: dict, now: float, key_type) -> dict:
        rates: dict = {}
        new_prev: dict = {}
        for key, (rx_total, tx_total) in current.items():
            if rx_total == 0 and tx_total == 0:
                continue
            old = prev.get(key)
            if old is not None:
                old_t, old_rx, old_tx = old
                dt = now - old_t
                if dt > 0 and rx_total >= old_rx and tx_total >= old_tx:
                    rx = (rx_total - old_rx) / dt
                    tx = (tx_total - old_tx) / dt
                    if rx >= _MIN_RATE or tx >= _MIN_RATE:
                        rates[key] = {"rx": round(rx, 1), "tx": round(tx, 1)}
            new_prev[key] = (now, rx_total, tx_total)
        prev.clear()
        prev.update(new_prev)
        return rates

    def reset(self) -> None:
        self._pid_prev.clear()
        self._conn_prev.clear()
        self.pid_rates = {}
        self.conn_rates = {}


def demo_rates(connections: list[Connection], now: float) -> tuple[dict, dict]:
    """Deterministic synthetic rates so demo mode shows per-app bandwidth."""
    pid_rates: dict[int, dict] = {}
    conn_rates: dict = {}
    for c in connections:
        if not c.remote_ip:
            continue
        seed = (c.pid * 31 + c.local_port) % 97
        base = 30_000 + (seed * 21_000) % 900_000
        wave = 0.55 + 0.45 * math.sin(now / 4.0 + seed % 13)
        rx = base * wave
        tx = base * wave * (0.18 + (seed % 5) * 0.05)
        conn_rates[c.conn_id] = {"rx": round(rx, 1), "tx": round(tx, 1)}
        agg = pid_rates.setdefault(c.pid, {"rx": 0.0, "tx": 0.0})
        agg["rx"] = round(agg["rx"] + rx, 1)
        agg["tx"] = round(agg["tx"] + tx, 1)
    return pid_rates, conn_rates
