"""kb-local MCP Server:暴露 kb_search / kb_status 给 Claude Code / Cursor 等 MCP 客户端。

用法:
    uv run python -m kb_mcp
"""

from pathlib import Path
from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from kb_core.config import Settings, load_settings
from kb_core.pipelines.retrieval import RetrievalPipeline
from kb_core.stores.sqlite_store import SQLiteStore

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


def _get_retrieval() -> RetrievalPipeline:
    if "retrieval" not in _state:
        from kb_cli.commands.jobs import _build_pipeline

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
    return cast(RetrievalPipeline, _state["retrieval"])


@mcp.tool()
def kb_search(
    query: str,
    top_k: int = 10,
    project: str | None = None,
    threshold: float = 0.3,
    rerank: bool = False,
) -> str:
    """搜索本地 RAG 知识库。返回最相关的代码块/文档片段(带行号引用)。

    Args:
        query: 自然语言查询(中英文均可)
        top_k: 最大返回数量(默认 10)
        project: 限定项目名(可选)
        threshold: 相关度阈值 0.0-1.0,默认 0.3
        rerank: 是否启用 reranker 精排(默认关闭,准确但慢)
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
        return f"未找到匹配结果(query={query!r})"

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
