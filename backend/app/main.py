"""FastAPI application: REST + WebSocket front door for GhostNet."""

from __future__ import annotations

import argparse
import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .monitor.collector import NetworkCollector
from .monitor.demo import DemoSource
from .monitor.macos import detect_source
from .services.dns import DnsResolver
from .services.history import EventStore
from .websocket.manager import ConnectionManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("ghostnet")


def create_app(
    demo: bool = False,
    poll_interval: float = 1.5,
    db_path: str | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        source = DemoSource() if demo else detect_source()
        manager: ConnectionManager = app.state.manager
        store = EventStore(db_path)

        async def emit(event: dict) -> None:
            await manager.broadcast(event)

        collector = NetworkCollector(
            source=source,
            resolver=DnsResolver(),
            emit=emit,
            poll_interval=poll_interval,
            demo=demo,
            store=store,
        )
        app.state.collector = collector
        task = asyncio.create_task(collector.run())
        log.info("GhostNet up (source=%s demo=%s)", source.name, demo)
        try:
            yield
        finally:
            collector.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            store.close()

    app = FastAPI(title="GhostNet", version="0.1.0", lifespan=lifespan)
    app.state.manager = ConnectionManager()
    app.state.collector = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        manager: ConnectionManager = app.state.manager
        collector: NetworkCollector | None = app.state.collector
        await manager.connect(ws)
        try:
            if collector is not None:
                await ws.send_json({"type": "snapshot", **collector.snapshot()})
            while True:
                await ws.receive_text()  # clients may ping; payload ignored
        except WebSocketDisconnect:
            manager.disconnect(ws)
        except Exception:
            manager.disconnect(ws)

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True}

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="GhostNet backend")
    parser.add_argument("--demo", action="store_true", help="synthetic traffic (no sudo needed)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--interval", type=float, default=1.5, help="poll interval seconds")
    args = parser.parse_args()
    uvicorn.run(
        create_app(demo=args.demo, poll_interval=args.interval),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
