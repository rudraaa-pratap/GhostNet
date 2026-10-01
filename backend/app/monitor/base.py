"""Core data models and the OS-source abstraction for GhostNet."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

FAMILY_INET4 = "inet4"
FAMILY_INET6 = "inet6"


@dataclass(frozen=True, slots=True)
class RawConnection:
    """A single socket as reported by the OS, before enrichment."""

    pid: int
    process: str
    protocol: str  # "tcp" | "udp"
    family: str  # FAMILY_INET4 | FAMILY_INET6
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    status: str
    hostname_hint: str = ""  # demo/synthetic sources may provide a name directly

    @property
    def key(self) -> str:
        return (
            f"{self.pid}:{self.protocol}:{self.local_ip}:{self.local_port}:"
            f"{self.remote_ip}:{self.remote_port}"
        )

    @property
    def has_remote(self) -> bool:
        return bool(self.remote_ip)


@dataclass(slots=True)
class Connection:
    """An enriched, stable connection record surfaced to the API/UI."""

    conn_id: str
    pid: int
    process: str
    protocol: str
    family: str
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    status: str
    hostname: str = ""
    registrable: str = ""  # eTLD+1 of hostname (google.com)
    category: str = ""  # Ads, Google, CDN, …
    rx_bps: float = 0.0  # per-connection download rate (from nettop)
    tx_bps: float = 0.0  # per-connection upload rate
    opened_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    @property
    def domain(self) -> str:
        """Best available label for the remote endpoint."""
        return self.hostname or (self.remote_ip if self.remote_ip else "listening")

    @classmethod
    def from_raw(cls, raw: RawConnection) -> Connection:
        return cls(
            conn_id=raw.key,
            pid=raw.pid,
            process=raw.process,
            protocol=raw.protocol,
            family=raw.family,
            local_ip=raw.local_ip,
            local_port=raw.local_port,
            remote_ip=raw.remote_ip,
            remote_port=raw.remote_port,
            status=raw.status,
            hostname=raw.hostname_hint,
        )

    def to_dict(self) -> dict:
        return asdict(self) | {"domain": self.domain}


class ConnectionSource(ABC):
    """Abstracts OS-specific socket enumeration so Linux/Windows can plug in later."""

    name: str = "unknown"

    @property
    @abstractmethod
    def elevated(self) -> bool:
        """True when the source can see other users' connections (system-wide)."""

    @abstractmethod
    def snapshot(self) -> list[RawConnection]:
        """Return the current socket list. Runs in a worker thread — may block."""

    def describe(self) -> dict:
        return {"source": self.name, "elevated": self.elevated}
