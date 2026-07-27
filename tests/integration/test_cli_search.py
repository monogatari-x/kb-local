from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kb_cli.commands import search as search_mod
from kb_cli.main import app


def test_search_returns_results(monkeypatch):
    from kb_core.enums import ChunkType
    from kb_core.models import Chunk, Document, SearchResult

    class FakeRetrieval:
        def search(self, query, top_k=10, filters=None, score_threshold=0.3):
            return [SearchResult(
                chunk=Chunk(chunk_id="c1", doc_id="d1", ordinal=0, text="hello",
                            tokens=1, content_hash="h", start_char=0, end_char=5,
                            start_line=1, end_line=1, chunk_type=ChunkType.PARAGRAPH,
                            quality_score=1.0),
                document=Document(
                    doc_id="d1", source_path="/x", rel_path="x", project="p",
                    file_type="text", sha256="x", size_bytes=1,
                    mtime=datetime(2026, 7, 22), ingested_at=datetime(2026, 7, 22),
                ),
                final_score=0.9, vector_score=0.9, citation="x:1-1",
                highlights=[], prev_chunk_id=None, next_chunk_id=None,
            )]

    monkeypatch.setattr(search_mod, "_build_retrieval", lambda store, settings: FakeRetrieval())
    monkeypatch.setattr(search_mod, "_get_store", lambda cfg: _FakeStore())
    runner = CliRunner()
    result = runner.invoke(app, ["search", "hello"])
    assert result.exit_code == 0, result.stdout
    assert "hello" in result.stdout
    assert "x:1-1" in result.stdout


def test_search_no_results(monkeypatch):
    class FakeRetrieval:
        def search(self, *a, **kw):
            return []

    monkeypatch.setattr(search_mod, "_build_retrieval", lambda store, settings: FakeRetrieval())
    monkeypatch.setattr(search_mod, "_get_store", lambda cfg: _FakeStore())
    runner = CliRunner()
    result = runner.invoke(app, ["search", "nothing"])
    assert result.exit_code == 0
    assert "未找到" in result.stdout or "无匹配" in result.stdout


class _FakeStore:
    def close(self) -> None:
        return None


@pytest.fixture
def store_fixture(tmp_path: Path):
    from kb_core.stores.sqlite_store import SQLiteStore

    s = SQLiteStore(tmp_path / "t.db")
    s.init_schema()
    s.close = lambda: None
    return s
