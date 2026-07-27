from pathlib import Path

import pytest
from typer.testing import CliRunner

from kb_cli.commands import add as add_mod
from kb_cli.main import app


def test_add_single_file(store_fixture, monkeypatch, tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hello", encoding="utf-8")

    class FakePipeline:
        last = None

        def index_file(self, path, watch_dir, project_strategy, project_name):
            self.last = (str(path), project_name)
            return "fake-doc-id"

    fake = FakePipeline()
    monkeypatch.setattr(add_mod, "_get_store", lambda cfg: store_fixture)
    monkeypatch.setattr(add_mod, "_build_pipeline", lambda store, settings: fake)
    runner = CliRunner()
    result = runner.invoke(app, ["add", str(src), "--project", "manual"])
    assert result.exit_code == 0, result.stdout
    assert fake.last == (str(src), "manual")


@pytest.fixture
def store_fixture(tmp_path: Path):
    from kb_core.stores.sqlite_store import SQLiteStore

    s = SQLiteStore(tmp_path / "t.db")
    s.init_schema()
    s.close = lambda: None
    return s
