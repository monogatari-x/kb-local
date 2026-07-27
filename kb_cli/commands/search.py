from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from kb_core.config import Settings, load_settings
from kb_core.pipelines.retrieval import RetrievalPipeline
from kb_core.stores.sqlite_store import SQLiteStore

console = Console()


def _load_settings(config: str | None) -> Settings:
    return load_settings(Path(config) if config else None)


def _get_store(settings: Settings) -> SQLiteStore:
    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    return store


def _build_retrieval(store: SQLiteStore, settings: Settings) -> RetrievalPipeline:
    from kb_cli.commands.jobs import _build_pipeline

    pipeline = _build_pipeline(store, settings)
    return RetrievalPipeline(store, pipeline.qdrant_store, pipeline.embedder)


def search(
    query: str = typer.Argument(..., help="查询文本"),
    top_k: int = typer.Option(10, "--top-k"),
    project: str = typer.Option(None, "--project", help="限定 project"),
    threshold: float = typer.Option(0.3, "--threshold", help="分数阈值"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """检索知识库"""
    settings = _load_settings(config)
    store = _get_store(settings)
    retrieval = _build_retrieval(store, settings)

    filters: dict[str, Any] | None = None
    if project:
        filters = {"must": [{"key": "project", "match": {"value": project}}]}

    results = retrieval.search(query, top_k=top_k, filters=filters, score_threshold=threshold)
    store.close()

    if not results:
        console.print("[yellow]未找到匹配结果[/yellow]")
        return

    for i, r in enumerate(results, 1):
        body = f"[bold]{r.chunk.text[:200]}[/bold]"
        if len(r.chunk.text) > 200:
            body += " ..."
        meta = (
            f"[dim]{r.citation}[/dim]\n"
            f"[dim]score={r.final_score:.3f}  type={r.chunk.chunk_type.value}[/dim]"
        )
        console.print(Panel(body, title=f"#{i}  {meta}", border_style="blue"))
