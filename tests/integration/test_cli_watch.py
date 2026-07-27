from pathlib import Path

import pytest
from typer.testing import CliRunner

from kb_cli.commands import watch
from kb_cli.main import app


@pytest.fixture
def store(tmp_path: Path):
    from kb_core.stores.sqlite_store import SQLiteStore

    s = SQLiteStore(tmp_path / "t.db")
    s.init_schema()
    s.close = lambda: None
    return s


def test_watch_add_and_list(store, monkeypatch):
    monkeypatch.setattr(watch, "_get_store", lambda cfg: store)
    runner = CliRunner()
    result = runner.invoke(app, [
        "watch", "add", "/tmp/x",
        "--project", "p1",
        "--strategy", "first_subdir",
    ])
    assert result.exit_code == 0, result.stdout
    dirs = store.list_watch_dirs()
    assert len(dirs) == 1
    assert dirs[0]["path"] == "/tmp/x"

    result = runner.invoke(app, ["watch", "list"])
    assert "/tmp/x" in result.stdout


def test_watch_remove(store, monkeypatch):
    monkeypatch.setattr(watch, "_get_store", lambda cfg: store)
    wid = store.add_watch_dir("/y", "p", "fixed", True, [])
    runner = CliRunner()
    result = runner.invoke(app, ["watch", "remove", str(wid)])
    assert result.exit_code == 0
    assert store.list_watch_dirs() == []
