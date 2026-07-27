import typer

app = typer.Typer()


@app.command("list")
def list_jobs() -> None:
    raise NotImplementedError
