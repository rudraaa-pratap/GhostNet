"""Data-mode selection: GHOSTNET_SOURCE env var and --demo precedence.

Real mode must stay the default; demo mode must be requested explicitly.
"""

from fastapi.testclient import TestClient

from app.main import SOURCE_ENV, create_app, resolve_demo
from app.monitor.macos import detect_source


def test_real_is_the_default(monkeypatch):
    monkeypatch.delenv(SOURCE_ENV, raising=False)
    assert resolve_demo() is False


def test_env_selects_demo(monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, "demo")
    assert resolve_demo() is True


def test_env_selects_real(monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, "real")
    assert resolve_demo() is False


def test_env_is_tolerant_of_case_and_whitespace(monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, "  Demo ")
    assert resolve_demo() is True


def test_unknown_env_value_falls_back_to_real(monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, "staging")
    assert resolve_demo() is False


def test_cli_flag_beats_env(monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, "real")
    assert resolve_demo(cli_demo=True) is True


def test_detected_real_source_is_not_demo():
    assert detect_source().name in ("psutil", "lsof")


def test_env_var_drives_create_app(tmp_path, monkeypatch):
    """An unset demo arg means "read the environment"."""
    monkeypatch.setenv(SOURCE_ENV, "demo")
    app = create_app(poll_interval=0.05, db_path=str(tmp_path / "env.db"))
    with TestClient(app) as client:
        status = client.get("/api/status").json()
    assert status["demo"] is True
    assert status["source"] == "demo"


def test_explicit_demo_false_beats_env(tmp_path, monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, "demo")
    app = create_app(demo=False, poll_interval=0.05, db_path=str(tmp_path / "real.db"))
    with TestClient(app) as client:
        status = client.get("/api/status").json()
    assert status["demo"] is False
    assert status["source"] in ("psutil", "lsof")
