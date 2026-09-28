"""kb-local MCP Server:暴露 kb_search / kb_status 给 Claude Code / Cursor 等 MCP 客户端。

用法:
    uv run python -m kb_mcp
"""

from __future__ import annotations

import functools
import os
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import anyio
from mcp.server.fastmcp import FastMCP

from kb_core.config import Settings, load_settings
from kb_core.stores.sqlite_store import SQLiteStore

if TYPE_CHECKING:
    from kb_core.pipelines.retrieval import RetrievalPipeline

Transport = Literal["stdio", "streamable-http"]

_HTTP_ALIASES = frozenset({"http", "streamable-http"})
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765


def _resolve_transport() -> Transport:
    raw = os.environ.get("KB_MCP_TRANSPORT", "stdio").strip().lower()
    return "streamable-http" if raw in _HTTP_ALIASES else "stdio"


def _resolve_host() -> str:
    return os.environ.get("KB_MCP_HOST", "").strip() or _DEFAULT_HOST


def _resolve_port() -> int:
    raw = os.environ.get("KB_MCP_PORT", "").strip()
    if not raw.isdigit():
        return _DEFAULT_PORT
    port = int(raw)
    return port if 1 <= port <= 65535 else _DEFAULT_PORT


mcp = FastMCP("kb-local", host=_resolve_host(), port=_resolve_port())

_state: dict[str, Any] = {}


def _get_settings() -> Settings:
    if "settings" not in _state:
        _state["settings"] = load_settings(None)
    return cast(Settings, _state["settings"])


def _get_store() -> SQLiteStore:
    if "store" not in _state:
        settings = _get_settings()
        sqlite_path = Path(settings.database.sqlite_path).expanduser()
        store = SQLiteStore(sqlite_path, check_same_thread=False)
        store.init_schema()
        _state["store"] = store
    return cast(SQLiteStore, _state["store"])


def _build_retrieval() -> RetrievalPipeline:
    from kb_cli.commands.jobs import _build_pipeline
    from kb_core.pipelines.retrieval import RetrievalPipeline

    settings = _get_settings()
    store = _get_store()
    pipeline = _build_pipeline(store, settings)
    retrieval = RetrievalPipeline(
        store,
        pipeline.qdrant_store,
        pipeline.embedder,
        reranker=None,
    )
    _state["pipeline"] = pipeline
    _state["retrieval"] = retrieval
    return retrieval


def _get_retrieval() -> RetrievalPipeline:
    if "retrieval" not in _state:
        _build_retrieval()
    return cast("RetrievalPipeline", _state["retrieval"])


def prewarm() -> None:
    """在 FastMCP 启动前(主线程)预加载 BGE-M3 模型。

    PyTorch 在 anyio 工作线程里首次加载会触发 GIL 死锁,导致 kb_search 永久卡死。
    在主线程预加载可避免此问题,后续搜索由已加载的模型处理,响应秒级。
    """
    try:
        _build_retrieval()
    except Exception as e:
        sys.stderr.write(
            f"[kb-local] prewarm failed: {type(e).__name__}: {e}\n"
            f"搜索工具将不可用。请确认 Qdrant 已启动 (docker compose up -d) "
            f"且模型已下载 (uv run python scripts/download_models.py)\n"
        )
        sys.stderr.flush()


def _do_search(query: str, top_k: int, project: str | None, threshold: float, rerank: bool) -> str:
    try:
        retrieval = _get_retrieval()
    except Exception as e:
        return (
            f"检索引擎初始化失败: {type(e).__name__}: {e}\n"
            f"可能原因: Qdrant 未启动或模型加载失败。\n"
            f"请确认: ① Docker 运行中(docker compose up -d) "
            f"② 模型已下载(uv run python scripts/download_models.py)\n"
            f"详情: {traceback.format_exc(limit=3)}"
        )

    filters: dict[str, Any] | None = None
    if project:
        filters = {"must": [{"key": "project", "match": {"value": project}}]}

    try:
        results = retrieval.search(
            query,
            top_k=top_k,
            filters=filters,
            score_threshold=threshold,
            rerank=rerank,
        )
    except Exception as e:
        return (
            f"检索失败: {type(e).__name__}: {e}\n"
            f"可能原因: Qdrant 连接断开或查询参数异常。\n"
            f"请确认: Docker 和 Qdrant 正在运行(docker compose ps)。\n"
            f"详情: {traceback.format_exc(limit=3)}"
        )

    if not results:
        return (
            f"未找到匹配结果(query={query!r})。\n"
            f"可能原因: ① 知识库还没索引到这个主题 "
            f"(让用户跑 `uv run kb jobs run --type full_scan`); "
            f"② 阈值过高(让用户重试 threshold=0.2 或更低)。\n"
            f"不要再重试本工具,如实告知用户。"
        )

    lines = [f"# 检索结果 ({len(results)} 条)\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"## #{i}  {r.citation}")
        lines.append(f"score={r.final_score:.3f}  type={r.chunk.chunk_type.value}")
        lines.append("")
        lines.append("```")
        lines.append(r.chunk.text)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def kb_search(
    query: str,
    top_k: int = 10,
    project: str | None = None,
    threshold: float = 0.3,
    rerank: bool = False,
) -> str:
    """搜索本地 RAG 知识库 — 跨项目的语义检索(BGE-M3 嵌入 + Qdrant 混合检索)。

    【一次调用就够】用最相关的 1-2 个关键词搜,不要拆分多次调用。
    例:用户问"驾驶舱登录怎么实现的",query="驾驶舱登录"即可,不要先搜"驾驶舱"再搜"登录"。

    【优先级】用户提到"知识库 / 检索 / 搜索 / 查一下"等关键词时,本工具是 PRIMARY 入口,
    优先于 grep / 内建 memory recall / 项目级 AGENTS.md。直接调用本工具,不要先 listMcpResources。

    何时调用:
    - "知识库里关于 X 的信息" / "本地知识库中查 Y"
    - "X 功能怎么实现" / "X 在哪个项目" / "X 设计/架构"
    - 用户跨多项目找东西(覆盖 C:/Glow/Projects/ 下所有索引过的项目)
    - 用户问历史决策、规范、约定(从 docs/CLAUDE.md/openspec 里搜)

    何时 NOT 调用:
    - 用户在当前打开的项目里改具体源代码 → 直接 Read
    - 用户明确指了文件路径 → 直接 Read
    - 我返回"未找到" → 真的没索引到,告诉用户跑 `kb jobs run`,不要重试

    Args:
        query: 自然语言查询(中英文均可,1-3 个核心关键词最佳,过长反而降低召回)
        top_k: 最大返回数量(默认 10)
        project: 限定项目名(可选,如 "yaf")
        threshold: 相关度阈值 0.0-1.0,默认 0.3(调低=更多结果)
        rerank: 启用 reranker 精排(默认关闭,准确但慢 ~1s)

    Returns:
        带行号引用的代码/文档片段,格式 "path:line-line (symbol)"。
        空结果时返回 "未找到匹配结果",此时不要重试,如实告知用户。
    """
    return await anyio.to_thread.run_sync(
        lambda: _do_search(query, top_k, project, threshold, rerank)
    )


def _do_status() -> str:
    try:
        store = _get_store()
        docs = store.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status = 'active'"
        ).fetchone()[0]
        chunks = store.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        watch_dirs = store.conn.execute("SELECT COUNT(*) FROM watch_dirs").fetchone()[0]
        jobs = store.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        cache = store.conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()[0]
        return (
            f"知识库状态:\n"
            f"- 监控目录: {watch_dirs}\n"
            f"- 活跃文档: {docs}\n"
            f"- 切片总数: {chunks}\n"
            f"- 任务记录: {jobs}\n"
            f"- 嵌入缓存: {cache}"
        )
    except Exception as e:
        return f"获取状态失败: {type(e).__name__}: {e}\n详情: {traceback.format_exc(limit=3)}"


@mcp.tool()
async def kb_status() -> str:
    """返回知识库当前状态:文档数、切片数、监控目录数等。"""
    return await anyio.to_thread.run_sync(_do_status)


async def _daily_incremental_loop(interval_seconds: float = 24 * 3600.0) -> None:
    """每日兜底增量:watcher 僵死/漏事件时,由常驻服务补扫一遍。

    启动 5 分钟后先跑一次,之后每 24h;无变化时只算文件 sha,秒级完成。
    """
    import asyncio

    from kb_cli.commands.jobs import scan_and_index

    await asyncio.sleep(300)
    while True:
        try:
            pipeline = cast(Any, _state.get("pipeline"))
            store = _get_store()
            if pipeline is None:
                pipeline = _build_retrieval()
                pipeline = cast(Any, _state["pipeline"])
            processed, failed = await anyio.to_thread.run_sync(
                functools.partial(scan_and_index, store, pipeline)
            )
            sys.stderr.write(
                f"[kb-local] daily incremental: {processed} processed, {failed} failed\n"
            )
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[kb-local] daily incremental failed: {type(e).__name__}: {e}\n")
            sys.stderr.flush()
        await asyncio.sleep(interval_seconds)


def _run_http_with_auth() -> None:
    import asyncio

    import uvicorn

    from kb_mcp.bearer_auth import BearerAuthMiddleware

    mcp.settings.stateless_http = True
    token = os.environ.get("KB_MCP_TOKEN", "").strip() or None
    app = BearerAuthMiddleware(app=mcp.streamable_http_app(), token=token)

    async def _serve() -> None:
        config = uvicorn.Config(
            app,
            host=_resolve_host(),
            port=_resolve_port(),
            log_level=mcp.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        background = asyncio.create_task(_daily_incremental_loop())
        try:
            await server.serve()
        finally:
            background.cancel()

    asyncio.run(_serve())


def main() -> None:
    prewarm()
    if _resolve_transport() == "streamable-http":
        _run_http_with_auth()
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
