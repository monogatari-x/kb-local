"""验证 MCP server 能否被外部客户端调用。

启动 stdio transport,通过 mcp 客户端 SDK 列工具 / 调工具,确认全链路通。

用法:
    uv run python scripts/verify_mcp.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify() -> int:
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
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"  可用工具: {tool_names}")
            assert "kb_search" in tool_names, "kb_search 未注册"
            assert "kb_status" in tool_names, "kb_status 未注册"

            print("[3/3] 调用 kb_status...")
            result = await session.call_tool("kb_status", {})
            first = result.content[0] if result.content else None
            text = getattr(first, "text", "") if first else ""
            print(f"  kb_status 返回:\n{text}\n")

    print("\n[OK] MCP server 验证通过。可以加到 Claude Code 配置中。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(verify()))
