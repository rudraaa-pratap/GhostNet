"""API + WebSocket integration tests (demo mode, ASGI in-process)."""

import time

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path, **kwargs) -> TestClient:
    app = create_app(
        demo=True,
        poll_interval=kwargs.pop("poll_interval", 0.05),
        db_path=str(tmp_path / "test.db"),
        **kwargs,
    )
    return TestClient(app)


def wait_for_conns(client, minimum=3, attempts=60):
    data = client.get("/api/connections").json()
    for _ in range(attempts):
        if data["count"] >= minimum:
            break
        time.sleep(0.05)
        data = client.get("/api/connections").json()
    return data


def test_status_and_health(tmp_path):
    with make_client(tmp_path) as client:
        status = client.get("/api/status").json()
        assert status["demo"] is True
        assert status["source"] == "demo"
        assert status["elevated"] is True
        assert status["bandwidth"] == "demo"
        assert client.get("/api/health").json() == {"ok": True}


def test_connections_and_processes(tmp_path):
    with make_client(tmp_path) as client:
        data = wait_for_conns(client)
        assert data["count"] >= 1
        c0 = data["connections"][0]
        for key in ("conn_id", "process", "pid", "protocol", "domain", "remote_ip", "status"):
            assert key in c0
        assert "registrable" in c0 and "category" in c0
        assert "rx_bps" in c0 and "tx_bps" in c0

        procs = client.get("/api/processes").json()
        assert procs["count"] == data["count"]
        assert all("rx_bps" in p and "tx_bps" in p for p in procs["processes"])

        stats = client.get("/api/stats").json()
        assert stats["stats"]["connections"] == data["count"]
        assert isinstance(stats["history"], list)
        assert "bandwidth" in stats


def test_connection_filters(tmp_path):
    with make_client(tmp_path) as client:
        data = wait_for_conns(client)
        all_conns = data["connections"]

        by_proto = client.get("/api/connections", params={"protocol": "tcp"}).json()
        assert all(c["protocol"] == "tcp" for c in by_proto["connections"])
        assert by_proto["count"] <= data["count"]

        first_app = all_conns[0]["process"]
        by_app = client.get("/api/connections", params={"app": first_app}).json()
        assert by_app["count"] >= 1
        assert all(c["process"] == first_app for c in by_app["connections"])

        # free-text search hits process name or domain
        needle = first_app.lower()[:4]
        by_q = client.get("/api/connections", params={"q": needle}).json()
        assert by_q["count"] >= 1
        assert all(
            needle in (c["process"] + c["domain"] + c["remote_ip"]).lower()
            for c in by_q["connections"]
        )

        by_status = client.get("/api/connections", params={"status": "ESTABLISHED"}).json()
        assert all(c["status"] == "ESTABLISHED" for c in by_status["connections"])


def test_domains_endpoint(tmp_path):
    with make_client(tmp_path) as client:
        wait_for_conns(client, minimum=4)
        data = client.get("/api/domains").json()
        assert data["count"] >= 1
        d0 = data["domains"][0]
        for key in ("domain", "category", "connections", "processes", "ips", "ports"):
            assert key in d0
        # demo hostnames categorize (google.com → Google, etc.)
        cats = {d["category"] for d in data["domains"]}
        assert cats <= {
            "Google",
            "GitHub",
            "Spotify",
            "Slack",
            "Developer",
            "CDN",
            "Other",
            "Pending",
            "IP",
        }


def test_timeline_endpoint(tmp_path):
    with make_client(tmp_path) as client:
        wait_for_conns(client, minimum=4)
        # events are persisted by the collector loop
        events = []
        for _ in range(40):
            events = client.get("/api/timeline").json()["events"]
            if len(events) >= 2:
                break
            time.sleep(0.1)
        assert len(events) >= 1
        e0 = events[0]
        for key in ("ts", "kind", "process", "domain", "category"):
            assert key in e0
        assert e0["kind"] in ("open", "close")
        # chronological order
        assert [e["ts"] for e in events] == sorted(e["ts"] for e in events)

        # explicit window filters
        future = client.get("/api/timeline", params={"since": time.time() + 60}).json()
        assert future["events"] == []


def test_websocket_snapshot_and_events(tmp_path):
    with make_client(tmp_path) as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["type"] == "snapshot"
            assert "connections" in first and "stats" in first and "status" in first
            assert "bandwidth" in first
            seen = {first["type"]}
            for _ in range(14):
                msg = ws.receive_json()
                seen.add(msg["type"])
                if msg["type"] == "stats":
                    assert "download_bps" in msg["stats"]
                if msg["type"] == "conn_open":
                    assert "ts" in msg and "connection" in msg
                if msg["type"] == "bandwidth":
                    assert "rates" in msg and "connections" in msg
            assert "stats" in seen
            assert "bandwidth" in seen
