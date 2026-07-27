"""初始化 SQLite schema 和 Qdrant collection。

用法:
    uv run python scripts/init_db.py [--config PATH]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console

from kb_core.config import load_settings
from kb_core.stores.qdrant_store import QdrantStore
from kb_core.stores.sqlite_store import SQLiteStore

console = Console()


def main(
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH"),
) -> None:
    settings = load_settings(Path(config) if config else None)

    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    console.print(f"[green]SQLite OK[/green] {sqlite_path}")
    store.close()

    qdrant = QdrantStore(url=settings.qdrant.url, collection=settings.qdrant.collection)
    qdrant.ensure_collection()
    console.print(f"[green]Qdrant OK[/green] {settings.qdrant.url}/{settings.qdrant.collection}")


if __name__ == "__main__":
    typer.run(main)
