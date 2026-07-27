import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from kb_core.config import Settings, WatchDirConfig, load_settings
from kb_core.enums import ProjectStrategy
from kb_core.pipelines.indexing import IndexingPipeline
from kb_core.stores.sqlite_store import SQLiteStore
from kb_core.utils.paths import match_exclude, rel_path

app = typer.Typer()
console = Console()


def _load_settings(config: str | None) -> Settings:
    return load_settings(Path(config) if config else None)


def _get_store(settings: Settings) -> SQLiteStore:
    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    return store


def _build_pipeline(store: SQLiteStore, settings: Settings) -> IndexingPipeline:
    from kb_core.chunkers.code_chunker import CodeChunker
    from kb_core.chunkers.markdown_chunker import MarkdownChunker
    from kb_core.chunkers.recursive_chunker import RecursiveChunker
    from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
    from kb_core.embeddings.cache import EmbeddingCache
    from kb_core.loaders.code_loader import CodeLoader
    from kb_core.loaders.markdown_loader import MarkdownLoader
    from kb_core.loaders.registry import LoaderRegistry
    from kb_core.pipelines.indexing import IndexingPipeline
    from kb_core.stores.qdrant_store import QdrantStore

    reg = LoaderRegistry()
    reg.register(CodeLoader())
    reg.register(MarkdownLoader())
    qdrant = QdrantStore(url=settings.qdrant.url, collection=settings.qdrant.collection)
    qdrant.ensure_collection()
    cache = (
        EmbeddingCache(store.conn, version=settings.embedding.version)
        if settings.embedding.cache_enabled
        else None
    )
    embedder = BGE_M3_EMBEDDER(
        model_name=settings.embedding.model,
        device=settings.embedding.device,
        cache=cache,
        batch_size=settings.embedding.batch_size_cpu,
    )
    chunkers = {
        "code": CodeChunker(),
        "markdown": MarkdownChunker(),
        "text": RecursiveChunker(),
    }
    return IndexingPipeline(store, qdrant, reg, embedder, chunkers, settings.chunking)


def _watch_dir_from_row(row: dict[str, Any]) -> WatchDirConfig:
    raw = row.get("exclude_patterns") or "[]"
    patterns = raw if isinstance(raw, list) else json.loads(raw)
    return WatchDirConfig(
        path=row["path"],
        project_name=row["project_name"],
        project_strategy=row["project_strategy"],
        recursive=row["recursive"],
        exclude_patterns=patterns,
    )


@app.command("run")
def run(
    type: str = typer.Option("incremental", "--type", help="full_scan | incremental"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """运行索引任务"""
    settings = _load_settings(config)
    store = _get_store(settings)
    job_id = store.create_job(type, trigger="manual")

    watch_dirs_cfg = list(settings.watch_dirs) or [
        _watch_dir_from_row(d) for d in store.list_watch_dirs()
    ]
    pipeline = _build_pipeline(store, settings)

    processed = 0
    failed = 0
    for wd in watch_dirs_cfg:
        root = Path(wd.path)
        if not root.exists():
            continue
        strategy = ProjectStrategy(wd.project_strategy)
        for current_root, _dirs, files in os.walk(root):
            for f in files:
                full = Path(current_root) / f
                rp = rel_path(full, root)
                if match_exclude(rp, wd.exclude_patterns):
                    continue
                try:
                    pipeline.index_file(full, root, strategy, wd.project_name)
                    processed += 1
                except Exception as e:
                    console.print(f"[red]FAIL[/red] {full}: {e}")
                    failed += 1
            if not wd.recursive:
                break

    store.update_job(
        job_id,
        status="success" if failed == 0 else "partial",
        finished_at=datetime.now().isoformat(),
        total_files=processed + failed,
        processed_files=processed,
        failed_files=failed,
    )
    console.print(
        f"[green]完成[/green] 成功 {processed}，失败 {failed}（job_id={job_id[:8]}）"
    )
    store.close()


@app.command("list")
def list_jobs(
    limit: int = typer.Option(20, "--limit"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """列出最近的任务"""
    settings = _load_settings(config)
    store = _get_store(settings)
    rows = store.list_jobs(limit)
    if not rows:
        console.print("[yellow]暂无任务记录[/yellow]")
        store.close()
        return
    table = Table("ID", "类型", "状态", "开始", "处理/失败")
    for j in rows:
        table.add_row(
            j["job_id"][:8],
            j["type"],
            j["status"],
            j["started_at"],
            f'{j.get("processed_files", 0)}/{j.get("failed_files", 0)}',
        )
    console.print(table)
    store.close()
