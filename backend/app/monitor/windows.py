"""Windows connection source.

``psutil.net_connections()`` works on Windows without any privilege — sockets
owned by other users and system services come back with ``pid=None``, so the
unprivileged view is limited to the current user. Running GhostNet as
Administrator lifts that limit. Elevation detection lives in the shared
:class:`~app.monitor.psutil_source.PsutilSource` (``IsUserAnAdmin``).

Per-connection bandwidth sampling has no Windows backend yet — ``nettop`` is
macOS-only — so the collector keeps psutil's global rates and reports
``bandwidth: off`` (see ``bandwidth.py``).
"""

from __future__ import annotations

from .base import ConnectionSource
from .psutil_source import PsutilSource

#: Windows uses the shared psutil implementation; only elevation differs.
WindowsSource = PsutilSource

__all__ = ["WindowsSource", "detect_source"]


def detect_source() -> ConnectionSource:
    """psutil always works on Windows (elevated or not) — no fallback needed."""
    return PsutilSource()
