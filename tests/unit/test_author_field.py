from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from kb_core.enums import ChunkType
from kb_core.models import Chunk, Document, FileType
from kb_core.pipelines.retrieval import RetrievalPipeline
from kb_core.stores.sqlite_store import SQLiteStore


def _doc(**overrides: object) -> Document:
    base: dict = {
        "doc_id": "d1",
        "source_path": "X:/p/docs/a.md",
        "rel_path": "p/docs/a.md",
        "project": "p",
        "author": "pingtao.cao",
        "file_type": FileType.MARKDOWN,
        "sha256": "abc",
        "size_bytes": 10,
        "mtime": datetime(2026, 9, 28, 12, 0, 0),
        "ingested_at": datetime(2026, 9, 28, 12, 0, 0),
    }
    base.update(overrides)
    return Document(**base)  # type: ignore[arg-type]


def test_document_author_roundtrip(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    store.upsert_document(_doc())
    loaded = store.get_document("d1")
    assert loaded is not None and loaded.author == "pingtao.cao"

    store.upsert_document(_doc(doc_id="d2", author="chenkuan"))
    assert store.get_document("d2").author == "chenkuan"  # type: ignore[union-attr]


class _FakeEmbedder:
    model_name = "fake"

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], list[list[int]]]:
        return [[0.1] * 8 for _ in texts], [[] for _ in texts]


def test_indexing_pipeline_writes_author(tmp_path: Path):
    import kb_core.pipelines.indexing as idx

    src = tmp_path / "a.md"
    src.write_text("# T\n\n正文\n", encoding="utf-8")
    from kb_core.chunkers.markdown_chunker import MarkdownChunker
    from kb_core.loaders.markdown_loader import MarkdownLoader
    from kb_core.loaders.registry import LoaderRegistry

    reg = LoaderRegistry()
    reg.register(MarkdownLoader())
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    pipeline = idx.IndexingPipeline(
        sqlite_store=store,
        qdrant_store=MagicMock(),
        registry=reg,
        embedder=_FakeEmbedder(),
        chunkers={"markdown": MarkdownChunker()},
        author="pingtao.cao",
    )
    doc_id = pipeline.index_file(src, tmp_path, "first_subdir", "t")
    assert store.get_document(doc_id).author == "pingtao.cao"  # type: ignore[union-attr]


def _chunk() -> Chunk:
    return Chunk(
        chunk_id="c1",
        doc_id="d1",
        ordinal=0,
        text="正文",
        tokens=2,
        content_hash="h",
        start_char=0,
        end_char=2,
        start_line=3,
        end_line=3,
        chunk_type=ChunkType.PARAGRAPH,
        quality_score=1.0,
    )


def test_citation_includes_author_when_present(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    pipeline = RetrievalPipeline(store, MagicMock(), MagicMock())
    assert pipeline._build_citation(_chunk(), _doc()) == "[pingtao.cao] p/docs/a.md:3-3"


def test_citation_omits_author_when_empty(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    pipeline = RetrievalPipeline(store, MagicMock(), MagicMock())
    assert pipeline._build_citation(_chunk(), _doc(author="")) == "p/docs/a.md:3-3"


def test_backup_retry_recovers_from_transient_failure(monkeypatch):
    from scripts import backup

    calls = {"n": 0}

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(args, capture_output=True, text=True):
        calls["n"] += 1
        if calls["n"] == 1:
            p = FakeProc()
            p.returncode = 255
            p.stderr = "Connection timed out"
            return p
        return FakeProc()

    monkeypatch.setattr(backup.time, "sleep", lambda s: None)
    monkeypatch.setattr(backup.subprocess, "run", fake_run)
    backup._run_with_retry(["ssh", "x"], "ssh test")
    assert calls["n"] == 2
