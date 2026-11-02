"""Path resolution for the packaged (PyInstaller) runtime.

Dev mode keeps the DB in the checkout and dashboard in frontend/dist;
a frozen bundle must switch to the per-user data folder and the bundled
``frontend_dist`` data folder instead.
"""

import sys

from app.main import frontend_dist_dir
from app.services import history


def test_frozen_dist_plus_bundled_dashboard(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("GHOSTNET_DIST", raising=False)
    assert frontend_dist_dir() == tmp_path / "frontend_dist"


def test_dev_dist_is_the_checkout(monkeypatch):
    monkeypatch.delenv("GHOSTNET_DIST", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    path = frontend_dist_dir()
    assert path.name == "dist"
    assert path.parent.name == "frontend"


def test_frozen_db_lives_in_the_user_data_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("GHOSTNET_DB", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # keep Linux behavior hermetic
    p = history.default_db_path()
    assert p.name == "ghostnet.db"
    assert p.parent.name == "GhostNet"


def test_dev_db_lives_in_the_checkout(monkeypatch, tmp_path):
    monkeypatch.delenv("GHOSTNET_DB", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    p = history.default_db_path()
    assert p.parent.name == "data"


def test_env_db_path_always_wins(monkeypatch, tmp_path):
    custom = tmp_path / "local.db"
    monkeypatch.setenv("GHOSTNET_DB", str(custom))
    assert history.default_db_path() == custom
