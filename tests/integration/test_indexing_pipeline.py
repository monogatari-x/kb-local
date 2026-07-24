from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture(scope="module")
def pipeline(qdrant_store_module, tmp_path_factory):
    from kb_core.chunkers.code_chunker import CodeChunker
    from kb_core.chunkers.markdown_chunker import MarkdownChunker
    from kb_core.chunkers.recursive_chunker import RecursiveChunker
    from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
    from kb_core.loaders.code_loader import CodeLoader
    from kb_core.loaders.markdown_loader import MarkdownLoader
    from kb_core.loaders.registry import LoaderRegistry
    from kb_core.pipelines.indexing import IndexingPipeline
    from kb_core.stores.sqlite_store import SQLiteStore

    reg = LoaderRegistry()
    reg.register(CodeLoader())
    reg.register(MarkdownLoader())
    db_path = tmp_path_factory.mktemp("index") / "t.db"
    sqlite_store = SQLiteStore(db_path)
    sqlite_store.init_schema()
    embedder = BGE_M3_EMBEDDER(device="cpu", batch_size=4)
    chunkers = {"code": CodeChunker(), "markdown": MarkdownChunker(), "text": RecursiveChunker()}
    return IndexingPipeline(
        sqlite_store=sqlite_store,
        qdrant_store=qdrant_store_module,
        registry=reg,
        embedder=embedder,
        chunkers=chunkers,
    )


def test_index_php_file(pipeline, tmp_path: Path):
    src = tmp_path / "a.php"
    src.write_text("<?php\nclass A { function b() { return 1; } }\n", encoding="utf-8")
    doc_id = pipeline.index_file(
        src, watch_dir=tmp_path,
        project_strategy="first_subdir", project_name="test",
    )
    assert doc_id
    doc = pipeline.sqlite_store.get_document(doc_id)
    assert doc is not None
    chunks = pipeline.sqlite_store.get_chunks_by_doc(doc_id)
    assert len(chunks) >= 1


def test_reindex_updates(pipeline, tmp_path: Path):
    src = tmp_path / "a.py"
    src.write_text("def f():\n    return 1\n", encoding="utf-8")
    id1 = pipeline.index_file(
        src, watch_dir=tmp_path, project_strategy="first_subdir", project_name="t",
    )
    src.write_text("def g():\n    return 2\n", encoding="utf-8")
    id2 = pipeline.index_file(
        src, watch_dir=tmp_path, project_strategy="first_subdir", project_name="t",
    )
    assert id1 == id2
    chunks = pipeline.sqlite_store.get_chunks_by_doc(id1)
    assert len(chunks) == 1
    assert "def g" in chunks[0].text


def test_remove_document(pipeline, tmp_path: Path):
    src = tmp_path / "rm.py"
    src.write_text("x = 1\n", encoding="utf-8")
    doc_id = pipeline.index_file(
        src, watch_dir=tmp_path, project_strategy="first_subdir", project_name="t",
    )
    pipeline.remove_document(doc_id)
    assert pipeline.sqlite_store.get_document(doc_id) is None
    assert pipeline.sqlite_store.get_chunks_by_doc(doc_id) == []
