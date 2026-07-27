import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_retrieval_with_rerank_smoke(setup_index):
    """rerank=True 不报错,返回数量 <= top_k。"""
    retrieval = setup_index["retrieval"]
    results = retrieval.search("function b", top_k=5, rerank=True)
    assert len(results) <= 5


def test_retrieval_rerank_records_rerank_score(setup_index, tmp_path_factory):
    """启用 reranker 后,SearchResult.rerank_score > 0。"""
    from kb_core.embeddings.reranker import Reranker
    from kb_core.pipelines.retrieval import RetrievalPipeline

    store = setup_index["store"]
    qdrant = setup_index["qdrant"]
    embedder = setup_index["embedder"]
    reranker = Reranker()
    retrieval = RetrievalPipeline(store, qdrant, embedder, reranker=reranker)
    results = retrieval.search("function b", top_k=3, rerank=True)
    if results:
        assert all(r.rerank_score >= 0 for r in results)
        assert results[0].rerank_score > 0
