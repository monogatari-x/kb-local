from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kb_core.config import Settings, load_settings
from kb_core.stores.sqlite_store import SQLiteStore

console = Console()


def _load_settings(config: str | None) -> Settings:
    return load_settings(Path(config) if config else None)


def _get_store(settings: Settings) -> SQLiteStore:
    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    return store


def show(
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """显示系统状态"""
    settings = _load_settings(config)
    store = _get_store(settings)

    docs = store.conn.execute(
        "SELECT COUNT(*) FROM documents WHERE status = 'active'"
    ).fetchone()[0]
    chunks = store.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    watch_dirs = store.conn.execute("SELECT COUNT(*) FROM watch_dirs").fetchone()[0]
    jobs = store.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    cache = store.conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()[0]

    table = Table("项", "数量", title="知识库状态")
    table.add_row("监控目录", str(watch_dirs))
    table.add_row("活跃文档", str(docs))
    table.add_row("切片总数", str(chunks))
    table.add_row("任务记录", str(jobs))
    table.add_row("嵌入缓存", str(cache))
    console.print(table)
    console.print(f"[dim]SQLite: {store.db_path}[/dim]")
    console.print(f"[dim]Qdrant: {settings.qdrant.url}/{settings.qdrant.collection}[/dim]")
    store.close()
