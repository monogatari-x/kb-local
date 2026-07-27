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
