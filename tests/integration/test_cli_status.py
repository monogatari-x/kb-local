from pathlib import Path

import pytest
from typer.testing import CliRunner

from kb_cli.commands import status as status_mod
from kb_cli.main import app


def test_status_shows_counts(store_fixture, monkeypatch):
    monkeypatch.setattr(status_mod, "_get_store", lambda cfg: store_fixture)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.stdout
    assert "监控目录" in result.stdout or "documents" in result.stdout.lower()


@pytest.fixture
def store_fixture(tmp_path: Path):
    from kb_core.stores.sqlite_store import SQLiteStore

    s = SQLiteStore(tmp_path / "t.db")
    s.init_schema()
    s.close = lambda: None
    return s
