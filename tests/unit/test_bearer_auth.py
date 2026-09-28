from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from kb_mcp.bearer_auth import BearerAuthMiddleware


def _make_app(token: str | None) -> BearerAuthMiddleware:
    from starlette.routing import Route

    async def ok(request):  # type: ignore[no-untyped-def]
        return PlainTextResponse("ok")

    inner = Starlette(routes=[Route("/", ok, methods=["GET", "POST"])])
    return BearerAuthMiddleware(app=inner, token=token)


def test_no_token_configured_passes_through() -> None:
    client = TestClient(_make_app(token=None))
    assert client.get("/").status_code == 200


def test_valid_token_passes() -> None:
    client = TestClient(_make_app(token="secret"))
    assert client.get("/", headers={"Authorization": "Bearer secret"}).status_code == 200


def test_missing_token_rejected() -> None:
    client = TestClient(_make_app(token="secret"))
    assert client.get("/").status_code == 401


def test_wrong_token_rejected() -> None:
    client = TestClient(_make_app(token="secret"))
    assert client.get("/", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_malformed_header_rejected() -> None:
    client = TestClient(_make_app(token="secret"))
    assert client.get("/", headers={"Authorization": "secret"}).status_code == 401
    assert client.get("/", headers={"Authorization": "Basic secret"}).status_code == 401


def test_post_also_protected() -> None:
    client = TestClient(_make_app(token="secret"))
    assert client.post("/").status_code == 401
    assert client.post("/", headers={"Authorization": "Bearer secret"}).status_code == 200


def test_empty_token_means_disabled() -> None:
    client = TestClient(_make_app(token=""))
    assert client.get("/").status_code == 200
