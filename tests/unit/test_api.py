from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path):
    from kb_api.app import create_app
    from kb_core.config import DatabaseConfig, QdrantConfig, Settings
    from kb_core.stores.sqlite_store import SQLiteStore

    settings = Settings(
        database=DatabaseConfig(sqlite_path=str(tmp_path / "api.db")),
        qdrant=QdrantConfig(url="http://localhost:6333", collection="kb_api_test"),
    )
    store = SQLiteStore(Path(settings.database.sqlite_path), check_same_thread=False)
    store.init_schema()
    mock_retrieval = MagicMock()
    mock_retrieval.search.return_value = []
    app = create_app(
        store=store, settings=settings, bootstrap_pipeline=False, retrieval=mock_retrieval
    )
    return TestClient(app)


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_status_endpoint_returns_counts(client):
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert "documents" in body
    assert "chunks" in body
    assert "watch_dirs" in body


def test_search_endpoint_empty_kb(client):
    r = client.post("/search", json={"query": "anything"})
    assert r.status_code == 200
    assert r.json() == {"results": []}


def test_projects_endpoint_returns_distinct_projects(client):
    store = client.app.state.store
    cols = (
        "doc_id, source_path, rel_path, project, file_type, language, sha256, "
        "size_bytes, mtime, ingested_at, indexed_at, embedding_version, "
        "parser_version, status, error_msg, tags, meta"
    )
    for did, proj, rel in [("d1", "yaf", "a.md"), ("d2", "yaf", "b.md"), ("d3", "iam", "c.md")]:
        store.conn.execute(
            f"INSERT INTO documents({cols}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                did, f"p/{rel}", rel, proj, "md", "", "x", 1,
                "2026-07-29T00:00:00", "2026-07-29T00:00:00", "2026-07-29T00:00:00",
                "v1", "v1", "active", None, "[]", "{}",
            ),
        )
    r = client.get("/projects")
    assert r.status_code == 200
    projects = r.json()["projects"]
    assert sorted(projects) == ["iam", "yaf"]


def test_root_endpoint_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE html>" in r.text
