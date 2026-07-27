from unittest.mock import MagicMock


def test_kb_search_tool_returns_formatted_text(monkeypatch):
    from kb_mcp import server as server_mod

    mock_results = [MagicMock()]
    mock_results[0].chunk.text = "def login(user, pwd): ..."
    mock_results[0].chunk.chunk_type.value = "code_function"
    mock_results[0].citation = "auth.py:10-20 (login)"
    mock_results[0].final_score = 0.85
    mock_retrieval = MagicMock()
    mock_retrieval.search.return_value = mock_results
    monkeypatch.setattr(server_mod, "_get_retrieval", lambda: mock_retrieval)

    out = server_mod.kb_search("login logic")
    assert "login" in out
    assert "auth.py" in out
    assert "0.85" in out


def test_kb_search_tool_empty_results(monkeypatch):
    from kb_mcp import server as server_mod

    mock_retrieval = MagicMock()
    mock_retrieval.search.return_value = []
    monkeypatch.setattr(server_mod, "_get_retrieval", lambda: mock_retrieval)

    out = server_mod.kb_search("nothing matches")
    assert "未找到" in out or "no results" in out.lower() or "0 结果" in out


def test_kb_status_tool_returns_counts(monkeypatch):
    from kb_mcp import server as server_mod

    mock_store = MagicMock()
    mock_store.conn.execute.side_effect = [
        MagicMock(fetchone=lambda: [42]),
        MagicMock(fetchone=lambda: [500]),
        MagicMock(fetchone=lambda: [3]),
        MagicMock(fetchone=lambda: [10]),
        MagicMock(fetchone=lambda: [200]),
    ]
    monkeypatch.setattr(server_mod, "_get_store", lambda: mock_store)

    out = server_mod.kb_status()
    assert "42" in out
    assert "500" in out
