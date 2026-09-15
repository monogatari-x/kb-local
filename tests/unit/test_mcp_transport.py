import pytest

from kb_mcp import server as mcp_server
from kb_mcp.server import _resolve_host, _resolve_port, _resolve_transport


def test_default_transport_is_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KB_MCP_TRANSPORT", raising=False)
    assert _resolve_transport() == "stdio"


@pytest.mark.parametrize("raw", ["http", "HTTP", "  http  ", "streamable-http"])
def test_http_aliases_resolve_to_streamable_http(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("KB_MCP_TRANSPORT", raw)
    assert _resolve_transport() == "streamable-http"


@pytest.mark.parametrize("raw", ["stdio", "", "bogus", "sse"])
def test_unknown_transport_falls_back_to_stdio(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("KB_MCP_TRANSPORT", raw)
    assert _resolve_transport() == "stdio"


def test_default_host_is_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KB_MCP_HOST", raising=False)
    assert _resolve_host() == "127.0.0.1"


def test_blank_host_falls_back_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KB_MCP_HOST", "   ")
    assert _resolve_host() == "127.0.0.1"


def test_host_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KB_MCP_HOST", "0.0.0.0")
    assert _resolve_host() == "0.0.0.0"


def test_default_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KB_MCP_PORT", raising=False)
    assert _resolve_port() == 8765


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("9000", 9000), ("1", 1), ("65535", 65535), ("0", 8765), ("65536", 8765), ("abc", 8765)],
)
def test_port_validation(monkeypatch: pytest.MonkeyPatch, raw: str, expected: int) -> None:
    monkeypatch.setenv("KB_MCP_PORT", raw)
    assert _resolve_port() == expected


def test_mcp_instance_built_from_resolvers() -> None:
    assert mcp_server.mcp.settings.host == _resolve_host()
    assert mcp_server.mcp.settings.port == _resolve_port()
