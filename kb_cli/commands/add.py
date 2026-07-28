from pathlib import Path

import typer
from rich.console import Console

from kb_core.config import Settings, load_settings
from kb_core.enums import ProjectStrategy
from kb_core.pipelines.indexing import IndexingPipeline
from kb_core.stores.sqlite_store import SQLiteStore

console = Console()


def _load_settings(config: str | None) -> Settings:
    return load_settings(Path(config) if config else None)


def _get_store(settings: Settings) -> SQLiteStore:
    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    return store


def _build_pipeline(store: SQLiteStore, settings: Settings) -> IndexingPipeline:
    from kb_cli.commands.jobs import _build_pipeline as _bp

    return _bp(store, settings)


def add(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, help="要添加的文件"),
    project: str = typer.Option("manual", "--project", help="所属项目名"),
    strategy: str = typer.Option("fixed", "--strategy", help="fixed | first_subdir"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """添加单个文件到知识库"""
    settings = _load_settings(config)
    store = _get_store(settings)
    pipeline = _build_pipeline(store, settings)
    watch_dir = path.parent
    try:
        doc_id = pipeline.index_file(path, watch_dir, ProjectStrategy(strategy), project)
        console.print(f"[green]已索引[/green] {path} (doc_id={doc_id[:8]})")
    except Exception as e:
        console.print(f"[red]失败[/red] {path}: {e}")
        raise typer.Exit(code=2) from e
    finally:
        store.close()
