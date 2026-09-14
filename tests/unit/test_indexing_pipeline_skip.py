from pathlib import Path
from typing import Any

from kb_core.chunkers.markdown_chunker import MarkdownChunker
from kb_core.loaders.markdown_loader import MarkdownLoader
from kb_core.loaders.registry import LoaderRegistry
from kb_core.pipelines.indexing import PARSER_VERSION, IndexingPipeline
from kb_core.stores.sqlite_store import SQLiteStore


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], list[Any]]:
        self.calls += 1
        return [[0.1] * 8 for _ in texts], [[] for _ in texts]


class FakeQdrant:
    def __init__(self) -> None:
        self.upserts = 0
        self.deletes = 0

    def upsert_chunks(self, chunks: list[Any], dense: Any, sparse: Any) -> None:
        self.upserts += 1

    def delete_by_doc(self, doc_id: str) -> None:
        self.deletes += 1


def _make_pipeline(db_path: Path) -> tuple[IndexingPipeline, FakeEmbedder, FakeQdrant]:
    reg = LoaderRegistry()
    reg.register(MarkdownLoader())
    store = SQLiteStore(db_path)
    store.init_schema()
    embedder = FakeEmbedder()
    qdrant = FakeQdrant()
    pipeline = IndexingPipeline(
        sqlite_store=store,
        qdrant_store=qdrant,
        registry=reg,
        embedder=embedder,
        chunkers={"markdown": MarkdownChunker()},
    )
    return pipeline, embedder, qdrant


def test_unchanged_file_with_same_parser_version_skips(tmp_path: Path):
    pipeline, embedder, _ = _make_pipeline(tmp_path / "t1.db")
    src = tmp_path / "a.md"
    src.write_text("# T\n\n正文内容甲\n", encoding="utf-8")
    pipeline.index_file(src, tmp_path, "first_subdir", "t")
    calls_after_first = embedder.calls
    pipeline.index_file(src, tmp_path, "first_subdir", "t")
    assert embedder.calls == calls_after_first


def test_stale_parser_version_forces_rechunk(tmp_path: Path):
    pipeline, _, _ = _make_pipeline(tmp_path / "t2.db")
    src = tmp_path / "b.md"
    src.write_text("# T\n\n正文内容乙\n", encoding="utf-8")
    doc_id = pipeline.index_file(src, tmp_path, "first_subdir", "t")
    pipeline.sqlite_store.conn.execute(
        "UPDATE documents SET parser_version = ? WHERE doc_id = ?",
        ("0.0.1", doc_id),
    )
    pipeline.sqlite_store.conn.commit()
    pipeline.sqlite_store.delete_chunks_of_doc(doc_id)
    new_id = pipeline.index_file(src, tmp_path, "first_subdir", "t")
    assert new_id == doc_id
    doc = pipeline.sqlite_store.get_document(doc_id)
    assert doc is not None and doc.parser_version == PARSER_VERSION
    chunks = pipeline.sqlite_store.get_chunks_by_doc(doc_id)
    assert any("正文内容乙" in c.text for c in chunks)
