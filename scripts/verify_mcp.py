"""验证 MCP server 能否被外部客户端调用。

两种传输都支持:
    uv run python scripts/verify_mcp.py                       # stdio:自起子进程(默认)
    uv run python scripts/verify_mcp.py --transport http      # http:连已运行的服务

默认只查工具列表与 kb_status;加 --query 会额外跑一次 kb_search(需要模型已加载)。

用法:
    uv run python scripts/verify_mcp.py --query "登录逻辑"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

if TYPE_CHECKING:
    from mcp import ClientSession

DEFAULT_URL = "http://127.0.0.1:8765/mcp"
EXPECTED_TOOLS = frozenset({"kb_search", "kb_status"})


def _no_proxy_client_factory(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    """httpx 客户端:显式忽略环境代理。

    shell 里导出 SOCKS 代理时 httpx 会因缺 socksio 直接抛 ImportError,
    而本脚本要连的是本机端口,不需要任何代理。
    """
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout or httpx.Timeout(30.0),
        auth=auth,
        follow_redirects=True,
        trust_env=False,
    )


async def _check(session: ClientSession, query: str | None) -> int:
    await session.initialize()
    tools = await session.list_tools()
    names = {t.name for t in tools.tools}
    print(f"  可用工具: {sorted(names)}")

    missing = EXPECTED_TOOLS - names
    if missing:
        print(f"  [FAIL] 缺少工具: {sorted(missing)}")
        return 1

    print("[3/3] 调用 kb_status...")
    result = await session.call_tool("kb_status", {})
    first = result.content[0] if result.content else None
    text = getattr(first, "text", "") if first else ""
    print(f"  kb_status 返回:\n{text}\n")
    if not text.strip():
        print("  [FAIL] kb_status 返回空")
        return 1

    if query:
        print(f"[+] 调用 kb_search(query={query!r})...")
        hits = await session.call_tool("kb_search", {"query": query, "top_k": 3})
        hit_first = hits.content[0] if hits.content else None
        hit_text = getattr(hit_first, "text", "") if hit_first else ""
        preview = hit_text.strip().replace("\n", " ")[:200]
        print(f"  命中预览: {preview}\n")
        if not hit_text.strip():
            print("  [FAIL] kb_search 返回空")
            return 1

    return 0


async def verify_stdio(query: str | None) -> int:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "kb_mcp"],
        env={**os.environ, "HF_HUB_OFFLINE": "1"},
    )

    print("[1/3] 启动 kb_mcp 子进程(stdio transport)...")
    async with stdio_client(params) as (read, write):
        print("[2/3] 建立 MCP 会话...")
        async with ClientSession(read, write) as session:
            return await _check(session, query)


async def verify_http(url: str, query: str | None) -> int:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    print(f"[1/3] 连接 HTTP server: {url}")
    async with streamablehttp_client(url, httpx_client_factory=_no_proxy_client_factory) as (
        read,
        write,
        _get_session_id,
    ):
        print("[2/3] 建立 MCP 会话...")
        async with ClientSession(read, write) as session:
            return await _check(session, query)


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 kb-local MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio=自起子进程(默认);http=连已运行的服务",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"HTTP 端点,默认 {DEFAULT_URL}")
    parser.add_argument("--query", default=None, help="额外验证一次 kb_search(需模型已加载)")
    args = parser.parse_args()

    if args.transport == "http":
        rc = asyncio.run(verify_http(args.url, args.query))
    else:
        rc = asyncio.run(verify_stdio(args.query))

    if rc == 0:
        print("\n[OK] MCP server 验证通过。")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
