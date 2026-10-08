import shutil
import pytest
from bot import config


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Each test gets its own state, notes, dashboard folder and kill switch path."""
    notes = tmp_path / "notes"
    shutil.copytree(config.NOTES_DIR, notes)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(config, "NOTES_DIR", notes)
    monkeypatch.setattr(config, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(config, "KILL_SWITCH_FILE", tmp_path / "KILL_SWITCH")
    monkeypatch.setenv("DRY_RUN", "1")
    for k in ("EMAIL_USER", "EMAIL_APP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path
