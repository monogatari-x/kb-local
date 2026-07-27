import typer
from rich.console import Console

from kb_cli.commands import add, jobs, search, status, watch

app = typer.Typer(
    name="kb",
    help="本地 RAG 知识库命令行工具",
    no_args_is_help=True,
)
console = Console()

app.add_typer(watch.app, name="watch", help="管理监控目录")
app.add_typer(jobs.app, name="jobs", help="索引任务管理")
app.add_typer(search.app, name="search", help="检索知识库（直接传参模式）")
app.add_typer(status.app, name="status", help="查看系统状态")
app.command(name="add")(add.add)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", is_eager=True, help="显示版本号"),
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="配置文件路径"),
) -> None:
    """本地 RAG 知识库 CLI"""
    if version:
        console.print("kb 0.1.0")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()
    """本地 RAG 知识库 CLI"""
    if version:
        console.print("kb 0.1.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()
