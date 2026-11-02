"""Platform dispatch to the concrete OS connection sources.

``app.main`` imports ``detect_source`` from here, so adding a platform means
adding a ``<platform>.py`` module and one branch below — the collector, API
and UI never learn about it.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from .windows import detect_source
elif sys.platform == "darwin":
    from .macos import detect_source
else:  # linux and other unix-like platforms
    from .linux import detect_source

__all__ = ["detect_source"]
