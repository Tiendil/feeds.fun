
import typer
import uvicorn

app = typer.Typer()


@app.command()  # type: ignore
def echo(text: str) -> None:
    print(text)
