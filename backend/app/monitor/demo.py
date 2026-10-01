"""Synthetic connection source for demos and development without sudo."""

from __future__ import annotations

import random
import time

from .base import FAMILY_INET4, ConnectionSource, RawConnection

# (app, stable fake pid, [(domain, ip, remote port), ...])
_APPS: list[tuple[str, int, list[tuple[str, str, int]]]] = [
    (
        "Google Chrome",
        90101,
        [
            ("google.com", "142.250.196.110", 443),
            ("youtube.com", "142.250.196.206", 443),
            ("accounts.google.com", "142.250.72.164", 443),
            ("googleapis.com", "142.251.163.95", 443),
            ("cloudflare-dns.com", "104.16.248.249", 443),
        ],
    ),
    (
        "Code",
        90202,
        [
            ("github.com", "140.82.113.4", 443),
            ("api.github.com", "140.82.113.6", 443),
            ("marketplace.visualstudio.com", "13.107.246.40", 443),
            ("update.code.visualstudio.com", "13.107.213.70", 443),
        ],
    ),
    (
        "Spotify",
        90303,
        [
            ("audio-ak-spotify-com.akamaized.net", "23.62.14.86", 443),
            ("spotify.com", "35.186.224.35", 443),
            ("scdn.co", "13.225.87.196", 443),
        ],
    ),
    (
        "Slack",
        90404,
        [
            ("slack.com", "18.164.154.116", 443),
            ("slack-edge.com", "18.164.154.116", 443),
            ("files.slack.com", "18.164.154.116", 443),
        ],
    ),
    (
        "Terminal",
        90505,
        [
            ("registry.npmjs.org", "104.16.25.34", 443),
            ("pypi.org", "151.101.0.223", 443),
        ],
    ),
]


class DemoSource(ConnectionSource):
    """Generates a plausible, evolving connection mix (Chrome → github.com …)."""

    name = "demo"

    @property
    def elevated(self) -> bool:
        return True

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._active: dict[str, RawConnection] = {}
        self._next_local_port = 49152
        self._started = time.time()

    def _make(self) -> RawConnection:
        app, pid, endpoints = self._rng.choice(_APPS)
        domain, ip, port = self._rng.choice(endpoints)
        self._next_local_port = 49152 + (self._next_local_port - 49152 + 1) % 16383
        protocol = "udp" if self._rng.random() < 0.12 else "tcp"
        return RawConnection(
            pid=pid,
            process=app,
            protocol=protocol,
            family=FAMILY_INET4,
            local_ip="192.168.1.24",
            local_port=self._next_local_port,
            remote_ip=ip,
            remote_port=port,
            status="ESTABLISHED",
            hostname_hint=domain,
        )

    def snapshot(self) -> list[RawConnection]:
        # Ramp up over the first seconds so the graph animates in on startup.
        age = time.time() - self._started
        target = min(18, 4 + int(age / 2))
        if len(self._active) < target:
            raw = self._make()
            self._active[raw.key] = raw
        elif len(self._active) > target + 4:
            self._active.pop(self._rng.choice(list(self._active)), None)
        elif self._rng.random() < 0.45 and self._active:
            self._active.pop(self._rng.choice(list(self._active)), None)
            raw = self._make()
            self._active[raw.key] = raw
        return list(self._active.values())
