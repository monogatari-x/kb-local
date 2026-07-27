import typer

app = typer.Typer()


@app.command("show")
def show() -> None:
    raise NotImplementedError
