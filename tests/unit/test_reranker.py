import sys
from unittest.mock import MagicMock

import pytest

from kb_core.embeddings import reranker as reranker_mod


@pytest.fixture
def patched_flagreranker(monkeypatch):
    fake_mod = MagicMock()
    monkeypatch.setitem(sys.modules, "FlagEmbedding", fake_mod)
    return fake_mod


def test_rerank_returns_empty_for_empty_input(patched_flagreranker):
    r = reranker_mod.Reranker()
    assert r.rerank("q", []) == []


def test_rerank_sorts_by_score_descending(patched_flagreranker):
    r = reranker_mod.Reranker()
    r.model = MagicMock()
    r.model.compute_score.return_value = [0.1, 0.9, 0.5]
    result = r.rerank("q", ["a", "b", "c"])
    assert result == [(1, 0.9), (2, 0.5), (0, 0.1)]


def test_rerank_top_k_truncates(patched_flagreranker):
    r = reranker_mod.Reranker()
    r.model = MagicMock()
    r.model.compute_score.return_value = [0.1, 0.9, 0.5]
    result = r.rerank("q", ["a", "b", "c"], top_k=2)
    assert len(result) == 2
    assert result[0] == (1, 0.9)


def test_rerank_handles_single_document_scalar(patched_flagreranker):
    r = reranker_mod.Reranker()
    r.model = MagicMock()
    r.model.compute_score.return_value = 0.7
    result = r.rerank("q", ["a"])
    assert result == [(0, 0.7)]
