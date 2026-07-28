"""kb-local MCP Server:暴露 kb_search / kb_status 给 Claude Code / Cursor 等 MCP 客户端。

用法:
    uv run python -m kb_mcp
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from mcp.server.fastmcp import FastMCP

from kb_core.config import Settings, load_settings
from kb_core.stores.sqlite_store import SQLiteStore

if TYPE_CHECKING:
    from kb_core.pipelines.retrieval import RetrievalPipeline

mcp = FastMCP("kb-local")

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
    return cast(RetrievalPipeline, _state["retrieval"])


@mcp.tool()
def kb_search(
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
    retrieval = _get_retrieval()
    filters: dict[str, Any] | None = None
    if project:
        filters = {"must": [{"key": "project", "match": {"value": project}}]}
    results = retrieval.search(
        query,
        top_k=top_k,
        filters=filters,
        score_threshold=threshold,
        rerank=rerank,
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
def kb_status() -> str:
    """返回知识库当前状态:文档数、切片数、监控目录数等。"""
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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
