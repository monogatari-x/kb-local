import typer

app = typer.Typer()


@app.command("list")
def list_dirs() -> None:
    """列出所有监控目录"""
    raise NotImplementedError
