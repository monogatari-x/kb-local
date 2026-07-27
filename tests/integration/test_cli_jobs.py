from pathlib import Path

import pytest
from typer.testing import CliRunner

from kb_cli.commands import jobs
from kb_cli.main import app


def test_jobs_list_empty(store_fixture, monkeypatch):
    monkeypatch.setattr(jobs, "_get_store", lambda cfg: store_fixture)
    monkeypatch.setattr(jobs, "_build_pipeline", lambda *a, **kw: None)
    runner = CliRunner()
    result = runner.invoke(app, ["jobs", "list"])
    assert result.exit_code == 0
    assert "暂无" in result.stdout or "ID" in result.stdout


def test_jobs_run_full_scan(store_fixture, monkeypatch, tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hello", encoding="utf-8")
    store_fixture.add_watch_dir(str(tmp_path), "p", "fixed", False, [])

    class FakePipeline:
        indexed = []

        def index_file(self, path, watch_dir, project_strategy, project_name):
            self.indexed.append(str(path))
            return "fake-doc-id"

    fake = FakePipeline()
    monkeypatch.setattr(jobs, "_get_store", lambda cfg: store_fixture)
    monkeypatch.setattr(jobs, "_build_pipeline", lambda store, settings: fake)
    runner = CliRunner()
    result = runner.invoke(app, ["jobs", "run", "--type", "full_scan"])
    assert result.exit_code == 0, result.stdout
    assert any("x.txt" in p for p in fake.indexed)


@pytest.fixture
def store_fixture(tmp_path: Path):
    from kb_core.stores.sqlite_store import SQLiteStore

    s = SQLiteStore(tmp_path / "t.db")
    s.init_schema()
    s.close = lambda: None
    return s
