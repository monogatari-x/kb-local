from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kb_core.config import Settings, load_settings
from kb_core.stores.sqlite_store import SQLiteStore

app = typer.Typer()
console = Console()


def _get_store(settings: Settings) -> SQLiteStore:
    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    return store


def _load_settings(config: str | None) -> Settings:
    return load_settings(Path(config) if config else None)


@app.command("add")
def add(
    path: str = typer.Argument(..., help="要监控的目录"),
    project: str = typer.Option(..., "--project", help="项目名（逻辑分组）"),
    strategy: str = typer.Option("fixed", "--strategy", help="fixed | first_subdir"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive"),
    exclude: list[str] = typer.Option([], "--exclude", help="排除模式（可多次）"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """添加一个监控目录"""
    settings = _load_settings(config)
    store = _get_store(settings)
    wid = store.add_watch_dir(path, project, strategy, recursive, list(exclude))
    console.print(
        f"[green]已添加[/green] 监控目录 #{wid}: {path} "
        f"(project={project}, strategy={strategy})"
    )
    store.close()


@app.command("list")
def list_dirs(
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH"),
) -> None:
    """列出所有监控目录"""
    settings = _load_settings(config)
    store = _get_store(settings)
    dirs = store.list_watch_dirs()
    if not dirs:
        console.print("[yellow]暂无监控目录[/yellow]")
        store.close()
        return
    table = Table("ID", "路径", "项目", "策略", "递归", "排除")
    for d in dirs:
        table.add_row(
            str(d["id"]),
            d["path"],
            d["project_name"],
            d["project_strategy"],
            "是" if d["recursive"] else "否",
            d["exclude_patterns"] or "[]",
        )
    console.print(table)
    store.close()


@app.command("remove")
def remove(
    watch_id: int = typer.Argument(..., help="监控目录 ID"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH"),
) -> None:
    """移除监控目录（不删除已索引数据）"""
    settings = _load_settings(config)
    store = _get_store(settings)
    store.remove_watch_dir(watch_id)
    console.print(f"[green]已移除[/green] #{watch_id}")
    store.close()
