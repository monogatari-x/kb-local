from pathlib import Path

import pytest

from kb_core.embeddings.cache import EmbeddingCache
from kb_core.stores.sqlite_store import SQLiteStore


@pytest.fixture
def cache(tmp_path: Path) -> EmbeddingCache:
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    return EmbeddingCache(store.conn, version="bge-m3-v1")


def test_miss_then_hit(cache: EmbeddingCache):
    assert cache.get("h1") is None
    cache.put("h1", [0.1] * 8, {"indices": [0, 1], "values": [0.5, 0.5]})
    got = cache.get("h1")
    assert got is not None
    dense, sparse = got
    assert dense == pytest.approx([0.1] * 8, abs=1e-6)
    assert sparse["indices"] == [0, 1]
    assert sparse["values"] == [0.5, 0.5]


def test_version_isolation(cache: EmbeddingCache):
    cache.put("h1", [0.1] * 8, {"indices": [0], "values": [1.0]})
    cache_v2 = EmbeddingCache(cache.conn, version="bge-m3-v2")
    assert cache_v2.get("h1") is None


def test_stats_counts(cache: EmbeddingCache):
    cache.get("miss1")
    cache.put("h1", [0.1, 0.2], {"indices": [], "values": []})
    cache.get("h1")
    s = cache.stats()
    assert s["hits"] == 1
    assert s["misses"] == 1
    assert s["size"] == 1
