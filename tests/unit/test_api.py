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
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_status_endpoint_returns_counts(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert "documents" in body
    assert "chunks" in body
    assert "watch_dirs" in body


def test_search_endpoint_empty_kb(client):
    r = client.post("/api/search", json={"query": "anything"})
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
                did,
                f"p/{rel}",
                rel,
                proj,
                "md",
                "",
                "x",
                1,
                "2026-07-29T00:00:00",
                "2026-07-29T00:00:00",
                "2026-07-29T00:00:00",
                "v1",
                "v1",
                "active",
                None,
                "[]",
                "{}",
            ),
        )
    r = client.get("/api/projects")
    assert r.status_code == 200
    projects = r.json()["projects"]
    assert sorted(projects) == ["iam", "yaf"]


def test_root_endpoint_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE html>" in r.text


def _insert_doc(store, doc_id, project, status, rel, size, ingested):
    cols = (
        "doc_id, source_path, rel_path, project, file_type, language, sha256, "
        "size_bytes, mtime, ingested_at, indexed_at, embedding_version, "
        "parser_version, status, error_msg, tags, meta"
    )
    store.conn.execute(
        f"INSERT INTO documents({cols}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            doc_id,
            f"p/{rel}",
            rel,
            project,
            "md",
            "",
            "x",
            size,
            ingested,
            ingested,
            ingested,
            "v1",
            "v1",
            status,
            None,
            "[]",
            "{}",
        ),
    )


def test_documents_endpoint_returns_paginated(client):
    store = client.app.state.store
    for i in range(5):
        _insert_doc(store, f"d{i}", "yaf", "active", f"a{i}.md", 100 * i, "2026-07-29T00:00:00")
    r = client.get("/api/documents", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert {"doc_id", "project", "file_type", "status", "ingested_at"}.issubset(
        body["items"][0].keys()
    )


def test_documents_endpoint_filters_by_project(client):
    store = client.app.state.store
    _insert_doc(store, "d1", "yaf", "active", "a.md", 100, "2026-07-29T00:00:00")
    _insert_doc(store, "d2", "iam", "active", "b.md", 100, "2026-07-29T00:00:00")
    r = client.get("/api/documents", params={"project": "yaf"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["project"] == "yaf"


def test_documents_endpoint_filters_by_status(client):
    store = client.app.state.store
    _insert_doc(store, "d1", "yaf", "active", "a.md", 100, "2026-07-29T00:00:00")
    _insert_doc(store, "d2", "yaf", "error", "b.md", 100, "2026-07-29T00:00:00")
    r = client.get("/api/documents", params={"status": "error"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "error"


def test_documents_endpoint_filters_by_query(client):
    store = client.app.state.store
    _insert_doc(store, "d1", "yaf", "active", "login.md", 100, "2026-07-29T00:00:00")
    _insert_doc(store, "d2", "yaf", "active", "logout.md", 100, "2026-07-29T00:00:00")
    r = client.get("/api/documents", params={"q": "login"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert "login" in body["items"][0]["rel_path"]


def test_documents_endpoint_sorting_by_size(client):
    store = client.app.state.store
    _insert_doc(store, "d1", "yaf", "active", "a.md", 100, "2026-07-29T00:00:00")
    _insert_doc(store, "d2", "yaf", "active", "b.md", 500, "2026-07-29T00:00:00")
    r = client.get("/api/documents", params={"sort": "size_bytes", "order": "asc"})
    assert r.status_code == 200
    body = r.json()
    assert body["items"][0]["doc_id"] == "d1"
    assert body["items"][1]["doc_id"] == "d2"


def test_documents_endpoint_rejects_unknown_sort(client):
    r = client.get("/api/documents", params={"sort": "sha256"})
    assert r.status_code == 422
