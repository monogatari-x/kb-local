import math

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def embedder():
    from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER

    return BGE_M3_EMBEDDER(device="cpu", batch_size=4)


def test_vector_size(embedder):
    assert embedder.vector_size() == 1024


def test_embed_query_returns_correct_shapes(embedder):
    dense, sparse = embedder.embed_query("用户登录")
    assert len(dense) == 1024
    assert "indices" in sparse
    assert "values" in sparse
    assert len(sparse["indices"]) == len(sparse["values"])


def test_embed_batch_consistent(embedder):
    texts = ["hello", "world"]
    dense, sparse = embedder.embed_texts(texts)
    assert len(dense) == 2
    assert len(sparse) == 2
    d1, _ = embedder.embed_query("hello")
    d2, _ = embedder.embed_texts(["hello"])[0][0], None
    dot = sum(a * b for a, b in zip(d1, d2, strict=True))
    n1 = math.sqrt(sum(x * x for x in d1))
    n2 = math.sqrt(sum(x * x for x in d2))
    assert dot / (n1 * n2) > 0.99


def test_cache_hit_skips_inference(embedder, tmp_path):
    from kb_core.embeddings.cache import EmbeddingCache
    from kb_core.stores.sqlite_store import SQLiteStore

    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    cache = EmbeddingCache(store.conn, version="bge-m3-v1")
    embedder_with_cache = type(embedder)(device="cpu", batch_size=4, cache=cache)

    texts = ["cached text"]
    embedder_with_cache.embed_texts(texts)
    s1 = cache.stats()
    assert s1["size"] == 1
    embedder_with_cache.embed_texts(texts)
    s2 = cache.stats()
    assert s2["hits"] == 1
