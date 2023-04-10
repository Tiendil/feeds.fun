import typer
import uvicorn
from ffun.application.application import get_app, prepare_app

from ..application import app


@app.command()
def server(api: bool = False,
           loader: bool = False,
           librarian: bool = False) -> None:

    prepare_app(api=api, loader=loader, librarian=librarian)

    application = get_app()

    uvicorn.run(application)
