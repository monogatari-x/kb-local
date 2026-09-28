"""静态 Bearer token 鉴权的纯 ASGI middleware。

KB_MCP_TOKEN 未设置(或为空)时完全不介入;设置后所有请求必须携带
Authorization: Bearer <token>,否则 401。用于 kb-local MCP 服务暴露到
非回环地址时的最低限度防护,回环本机使用可不开。
"""

from __future__ import annotations

import json
from typing import Any

_UNAUTHORIZED_BODY = json.dumps({"error": "unauthorized"}).encode()


class BearerAuthMiddleware:
    def __init__(self, app: Any, token: str | None) -> None:
        self.app = app
        self.token = (token or "").strip()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or not self.token:
            await self.app(scope, receive, send)
            return
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        auth = headers.get("authorization", "")
        scheme, _, value = auth.partition(" ")
        if scheme.lower() != "bearer" or value.strip() != self.token:
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": _UNAUTHORIZED_BODY})
            return
        await self.app(scope, receive, send)
