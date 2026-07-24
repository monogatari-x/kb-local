import sqlite3
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent / "kb_core" / "stores" / "migrations"


@pytest.fixture
def sqlite_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.executescript(sql_file.read_text(encoding="utf-8"))
        conn.commit()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def qdrant_store_module():
    from testcontainers.qdrant import QdrantContainer

    container = QdrantContainer("qdrant/qdrant:v1.10.1")
    container.start()
    try:
        port = container.get_exposed_port(6333)
        from kb_core.stores.qdrant_store import QdrantStore

        store = QdrantStore(url=f"http://localhost:{port}", collection="kb_test_mvp")
        store.ensure_collection()
        yield store
    finally:
        container.stop()


@pytest.fixture(scope="module")
def setup_index(qdrant_store_module, tmp_path_factory):
    from kb_core.chunkers.code_chunker import CodeChunker
    from kb_core.chunkers.markdown_chunker import MarkdownChunker
    from kb_core.chunkers.recursive_chunker import RecursiveChunker
    from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
    from kb_core.loaders.code_loader import CodeLoader
    from kb_core.loaders.markdown_loader import MarkdownLoader
    from kb_core.loaders.registry import LoaderRegistry
    from kb_core.pipelines.indexing import IndexingPipeline
    from kb_core.pipelines.retrieval import RetrievalPipeline
    from kb_core.stores.sqlite_store import SQLiteStore

    tmp = tmp_path_factory.mktemp("retrieval")
    sqlite_store = SQLiteStore(tmp / "r.db")
    sqlite_store.init_schema()
    reg = LoaderRegistry()
    reg.register(CodeLoader())
    reg.register(MarkdownLoader())
    embedder = BGE_M3_EMBEDDER(device="cpu", batch_size=4)
    chunkers = {
        "code": CodeChunker(),
        "markdown": MarkdownChunker(),
        "text": RecursiveChunker(),
    }
    indexing = IndexingPipeline(sqlite_store, qdrant_store_module, reg, embedder, chunkers)
    retrieval = RetrievalPipeline(sqlite_store, qdrant_store_module, embedder)

    src = tmp / "a.php"
    src.write_text("<?php\nclass A { function b() { return 1; } }\n", encoding="utf-8")
    indexing.index_file(
        src, watch_dir=tmp, project_strategy="first_subdir", project_name="test",
    )
    return {"indexing": indexing, "retrieval": retrieval, "sqlite": sqlite_store}


