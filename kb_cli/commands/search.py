import typer

app = typer.Typer()


@app.command("run")
def run(query: str) -> None:
    raise NotImplementedError
