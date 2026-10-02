"""First-seen app → destination alerts (PDF §8 V3: "alerts")."""

from app.monitor.base import Connection
from app.services.aggregation import categorize, registrable_domain
from app.services.alerts import AlertWatcher, destination_key
from app.services.history import EventStore


def make_conn(process="Chrome", host="evil.example.com", ip="203.0.113.9", port=443, pid=4242):
    conn = Connection(
        conn_id=f"{pid}:{ip}",
        pid=pid,
        process=process,
        protocol="tcp",
        family="inet4",
        local_ip="192.168.1.24",
        local_port=50000,
        remote_ip=ip,
        remote_port=port,
        status="ESTABLISHED",
        hostname=host,
    )
    conn.registrable = registrable_domain(host)
    conn.category = categorize(host)
    return conn


def test_destination_key():
    assert destination_key(make_conn()) == ("Chrome", "example.com")

    listening = make_conn()
    listening.remote_ip = ""
    assert destination_key(listening) is None


def test_store_mark_seen_returns_only_unknown(tmp_path):
    store = EventStore(tmp_path / "ghostnet.db")
    assert store.mark_seen(["a|b", "c|d"]) == ["a|b", "c|d"]
    assert store.mark_seen(["a|b", "e|f"]) == ["e|f"]
    assert store.mark_seen([]) == []
    store.close()


def test_alert_store_roundtrip(tmp_path):
    store = EventStore(tmp_path / "ghostnet.db")
    assert store.alert_count() == 0

    rows = store.insert_alerts(
        [
            {
                "ts": 100.0,
                "process": "Chrome",
                "site": "evil.com",
                "category": "Other",
                "ip": "1.2.3.4",
                "port": 443,
            }
        ]
    )
    assert rows[0]["id"] >= 1

    recent = store.recent_alerts()
    assert len(recent) == 1
    assert recent[0]["process"] == "Chrome"
    assert recent[0]["site"] == "evil.com"
    assert store.alert_count() == 1
    store.close()


def test_watcher_bootstraps_silently_then_alerts(tmp_path):
    store = EventStore(tmp_path / "ghostnet.db")
    watcher = AlertWatcher(store, warmup_seconds=0)

    first = watcher.check([make_conn()])
    assert first == []  # baseline: never alert on pre-existing traffic

    # same destination again → still nothing
    assert watcher.check([make_conn()]) == []

    # a brand-new destination shows up → one alert
    fresh = watcher.check([make_conn(), make_conn(host="tracker.bad.net", ip="198.51.100.7")])
    assert len(fresh) == 1
    assert fresh[0]["process"] == "Chrome"
    assert fresh[0]["site"] == "bad.net"
    assert fresh[0]["id"] >= 1

    # persisted: a fresh watcher on the same DB does not re-fire it
    store.close()
    store2 = EventStore(tmp_path / "ghostnet.db")
    watcher2 = AlertWatcher(store2, warmup_seconds=0)
    assert watcher2.check([make_conn(), make_conn(host="tracker.bad.net", ip="198.51.100.7")]) == []
    store2.close()


def test_watcher_without_store_uses_memory_baseline():
    watcher = AlertWatcher(None, warmup_seconds=0)
    assert watcher.check([make_conn()]) == []  # seeds memory
    assert watcher.check([make_conn()]) == []
    alerts = watcher.check([make_conn(host="another.bad.net", ip="198.51.100.8")])
    assert len(alerts) == 1
    assert alerts[0]["site"] == "bad.net"


def test_watcher_skips_listening_sockets():
    watcher = AlertWatcher(None, warmup_seconds=0)
    listener = make_conn()
    listener.remote_ip = ""
    assert watcher.check([listener]) == []


def test_alerts_endpoint(tmp_path):
    import time

    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(demo=True, poll_interval=0.05, db_path=str(tmp_path / "api.db"))
    with TestClient(app) as client:
        for _ in range(60):
            if client.get("/api/connections").json()["count"] >= 4:
                break
            time.sleep(0.05)

        data = client.get("/api/alerts").json()
        assert {"alerts", "count", "total"} <= set(data)
        assert isinstance(data["alerts"], list)
        assert data["count"] == len(data["alerts"])
        for alert in data["alerts"]:
            assert {"id", "ts", "process", "site"} <= set(alert)


def test_watcher_warmup_swallows_startup_churn():
    watcher = AlertWatcher(None, warmup_seconds=60)
    assert watcher.check([make_conn()]) == []

    # a new destination during warm-up is recorded but stays silent
    assert watcher.check([make_conn(), make_conn(host="later.bad.net", ip="198.51.100.9")]) == []

    watcher.warmup_seconds = 0
    alerts = watcher.check([make_conn(), make_conn(host="even.later.net", ip="198.51.100.10")])
    assert len(alerts) == 1
    assert alerts[0]["site"] == "later.net"
