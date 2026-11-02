"""Linux connection source.

``psutil.net_connections()`` works unprivileged on Linux but can only read
sockets owned by processes of the current user (newer kernels may restrict
this further under ``hidepid``); running with sudo gives the full view.
"""

from __future__ import annotations

import psutil

from .base import ConnectionSource
from .psutil_source import PsutilSource

#: Linux is the one platform where psutil needs no native fallback.
LinuxSource = PsutilSource

__all__ = ["LinuxSource", "detect_source"]


def detect_source() -> ConnectionSource:
    """Prefer psutil; under hardened kernels surface an actionable error."""
    try:
        psutil.net_connections(kind="inet")
        return PsutilSource()
    except (OSError, PermissionError, psutil.AccessDenied):
        pass
    raise RuntimeError(
        "psutil.net_connections() unavailable (restricted procfs?) — "
        "re-run GhostNet with sudo for the system-wide view"
    )
