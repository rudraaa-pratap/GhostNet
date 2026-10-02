"""Export report endpoint (PDF §8 V3: "export")."""

import time

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path) -> TestClient:
    app = create_app(demo=True, poll_interval=0.05, db_path=str(tmp_path / "test.db"))
    return TestClient(app)


def test_report_snapshot(tmp_path):
    with make_client(tmp_path) as client:
        for _ in range(60):
            if client.get("/api/connections").json()["count"] >= 4:
                break
            time.sleep(0.05)

        # let the collector persist a few open/close events
        for _ in range(40):
            if client.get("/api/timeline").json()["count"] >= 2:
                break
            time.sleep(0.05)

        report = client.get("/api/report").json()

        assert report["generated_at"] > 0
        assert report["window"] == 24 * 3600
        assert report["status"]["demo"] is True
        assert report["stats"]["connections"] >= 1

        assert report["processes"], "expected per-app rows"
        assert {"process", "pids", "connections", "rx_bps", "tx_bps"} <= set(report["processes"][0])

        assert report["domains"], "expected domain rows"
        assert {"domain", "category", "connections", "processes"} <= set(report["domains"][0])

        assert report["connections"]
        first = report["connections"][0]
        assert {"conn_id", "pid", "protocol", "remote_port", "status"} <= set(first)

        timeline = report["timeline"]
        assert timeline["events"] >= 1
        assert timeline["opens"] + timeline["closes"] == timeline["events"]
        assert isinstance(timeline["hourly"], list)
        for bucket in timeline["hourly"]:
            assert {"hour", "opens", "closes"} <= set(bucket)


def test_report_window_filter(tmp_path):
    with make_client(tmp_path) as client:
        for _ in range(60):
            if client.get("/api/connections").json()["count"] >= 1:
                break
            time.sleep(0.05)

        wide = client.get("/api/report", params={"window": 86400}).json()
        narrow = client.get("/api/report", params={"window": 1}).json()
        assert wide["window"] == 86400
        assert narrow["window"] == 1
        assert narrow["timeline"]["events"] <= wide["timeline"]["events"]
