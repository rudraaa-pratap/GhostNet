"""SQLite event store tests."""

import time

from app.services.history import EventStore


def make_event(ts: float | None = None, kind: str = "open", **over) -> dict:
    base = {
        "ts": ts if ts is not None else time.time(),
        "kind": kind,
        "process": "Chrome",
        "pid": 1,
        "protocol": "tcp",
        "local_port": 50000,
        "remote_ip": "1.2.3.4",
        "remote_port": 443,
        "domain": "google.com",
        "registrable": "google.com",
        "category": "Google",
        "opened_at": ts if ts is not None else time.time(),
    }
    base.update(over)
    return base


def test_insert_and_query_roundtrip(tmp_path):
    store = EventStore(tmp_path / "t.db")
    now = time.time()
    store.insert_events([make_event(now - 10), make_event(now - 5, kind="close"), make_event(now)])
    assert store.count() == 3

    all_events = store.query(since=now - 60)
    assert len(all_events) == 3
    assert [e["kind"] for e in all_events] == ["open", "close", "open"]  # chronological

    only_open = store.query(since=now - 60, kind="open")
    assert len(only_open) == 2

    windowed = store.query(since=now - 7, until=now - 4)
    assert len(windowed) == 1
    assert windowed[0]["kind"] == "close"
    store.close()


def test_query_limit_returns_most_recent(tmp_path):
    store = EventStore(tmp_path / "t.db")
    now = time.time()
    store.insert_events([make_event(now - i) for i in range(50)])
    events = store.query(limit=10)
    assert len(events) == 10
    assert events[-1]["ts"] == now  # newest last (reversed chronological)
    store.close()


def test_prune_removes_old_events(tmp_path):
    store = EventStore(tmp_path / "t.db")
    now = time.time()
    store.insert_events([make_event(now - 100_000), make_event(now)])  # >24h old
    removed = store.prune()
    assert removed == 1
    assert store.count() == 1
    store.close()


def test_default_path_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GHOSTNET_DB", str(tmp_path / "env.db"))
    from app.services.history import default_db_path

    assert default_db_path() == tmp_path / "env.db"


def test_empty_insert_ok(tmp_path):
    store = EventStore(tmp_path / "t.db")
    assert store.insert_events([]) == 0
    assert store.query() == []
    store.close()
