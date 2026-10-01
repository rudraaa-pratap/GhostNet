"""WebSocket connection management — fan-out of collector events to clients."""

from __future__ import annotations

import logging

from fastapi import WebSocket

log = logging.getLogger("ghostnet.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        log.debug("ws connected (%d clients)", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, message: dict) -> None:
        if not self._clients:
            return
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
