"""Serving the built dashboard and CORS configuration.

The quality bar: without a built frontend nothing changes (the API keeps
working, no mount happens); with one, a single process serves both.
"""

from fastapi.testclient import TestClient

from app.main import allowed_origins, create_app, frontend_dist_dir


def test_allowed_origins_has_dev_default(monkeypatch):
    monkeypatch.delenv("GHOSTNET_ORIGINS", raising=False)
    assert "http://localhost:5173" in allowed_origins()


def test_allowed_origins_env_override(monkeypatch):
    monkeypatch.setenv("GHOSTNET_ORIGINS", "https://ghost.example, https://demo.ghost.dev ")
    assert allowed_origins() == ["https://ghost.example", "https://demo.ghost.dev"]


def test_frontend_dist_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("GHOSTNET_DIST", str(tmp_path / "custom"))
    assert frontend_dist_dir() == tmp_path / "custom"


def test_serves_built_frontend_from_one_process(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>ghostnet dashboard</h1>")
    monkeypatch.setenv("GHOSTNET_DIST", str(dist))

    app = create_app(demo=True, poll_interval=0.05, db_path=str(tmp_path / "static.db"))
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "ghostnet dashboard" in page.text
        # API and WS routes keep priority over the static mount
        assert client.get("/api/health").json() == {"ok": True}
        assert client.get("/api/status").json()["demo"] is True


def test_missing_dist_does_not_break_the_app(monkeypatch, tmp_path):
    """No built frontend → no mount, API-only app (existing behavior)."""
    monkeypatch.setenv("GHOSTNET_DIST", str(tmp_path / "missing"))
    app = create_app(demo=True, poll_interval=0.05, db_path=str(tmp_path / "no-dist.db"))
    routes = {getattr(r, "path", "") for r in app.routes}
    assert "/" not in routes
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"ok": True}


def test_cors_echoes_allowed_env_origin(monkeypatch, tmp_path):
    monkeypatch.setenv("GHOSTNET_ORIGINS", "https://ghost.example")
    app = create_app(demo=True, poll_interval=0.05, db_path=str(tmp_path / "cors.db"))
    with TestClient(app) as client:
        ok = client.get("/api/health", headers={"Origin": "https://ghost.example"})
        assert ok.headers.get("access-control-allow-origin") == "https://ghost.example"

        other = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert other.headers.get("access-control-allow-origin") != "https://evil.example"
