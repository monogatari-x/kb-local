import pytest

pytestmark = pytest.mark.integration


def _wait_qdrant():
    from testcontainers.qdrant import QdrantContainer

    return QdrantContainer("qdrant/qdrant:v1.10.1")


@pytest.fixture(scope="module")
def qdrant_store():
    container = _wait_qdrant()
    container.start()
    try:
        port = container.get_exposed_port(6333)
        from kb_core.stores.qdrant_store import QdrantStore

        store = QdrantStore(url=f"http://localhost:{port}", collection="test_kb")
        store.ensure_collection()
        yield store
    finally:
        container.stop()


def test_collection_created(qdrant_store):
    info = qdrant_store.client.get_collection("test_kb")
    assert info.config.params.vectors is not None


def test_upsert_and_search(qdrant_store):
    from kb_core.enums import ChunkType
    from kb_core.models import Chunk

    chunks = [
        Chunk(chunk_id="c1", doc_id="d1", ordinal=0, text="hello world",
              tokens=2, content_hash="h1", start_char=0, end_char=11,
              chunk_type=ChunkType.PARAGRAPH, quality_score=1.0),
        Chunk(chunk_id="c2", doc_id="d1", ordinal=1, text="another chunk",
              tokens=2, content_hash="h2", start_char=0, end_char=13,
              chunk_type=ChunkType.PARAGRAPH, quality_score=1.0),
    ]
    dense = [[0.1] * 1024, [0.9] * 1024]
    sparse = [
        {"indices": [0, 1], "values": [0.5, 0.5]},
        {"indices": [0, 1], "values": [1.0, 0.9]},
    ]
    qdrant_store.upsert_chunks(chunks, dense, sparse)

    results = qdrant_store.search_dense_sparse(
        dense=[0.95] * 1024,
        sparse={"indices": [0, 1], "values": [1.0, 0.9]},
        filters=None,
        limit=5,
    )
    assert len(results) >= 1
    top = results[0]
    assert top["chunk_id"] == "c2"


def test_filter_by_project(qdrant_store):
    results = qdrant_store.search_dense_sparse(
        dense=[0.1] * 1024,
        sparse={"indices": [0], "values": [1.0]},
        filters={"must": [{"key": "doc_id", "match": {"value": "d1"}}]},
        limit=10,
    )
    assert all(r["doc_id"] == "d1" for r in results)


def test_delete_by_doc(qdrant_store):
    qdrant_store.delete_by_doc("d1")
    results = qdrant_store.search_dense_sparse(
        dense=[0.1] * 1024,
        sparse={"indices": [0], "values": [1.0]},
        filters=None,
        limit=10,
    )
    assert all(r["doc_id"] != "d1" for r in results)
