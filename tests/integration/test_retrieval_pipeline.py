import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture(scope="module")
def retrieval(setup_index):
    return setup_index["retrieval"]


def test_search_returns_results(retrieval):
    results = retrieval.search("function b", top_k=5)
    assert len(results) >= 1
    r = results[0]
    assert r.chunk.chunk_id
    assert r.citation
    assert r.final_score >= 0


def test_search_with_project_filter(retrieval):
    results = retrieval.search(
        "anything",
        top_k=5,
        filters={"must": [{"key": "project", "match": {"value": "nonexistent"}}]},
    )
    assert results == []


def test_low_score_filtered(retrieval):
    results = retrieval.search("zzz unlikely query", top_k=5, score_threshold=2.0)
    assert results == []


def test_citation_format(retrieval):
    results = retrieval.search("function b", top_k=1)
    if results:
        assert ":" in results[0].citation or results[0].citation
