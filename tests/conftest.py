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

