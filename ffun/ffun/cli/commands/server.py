import typer
import uvicorn
from ffun.application.application import get_app

from ..application import app


@app.command()
def server() -> None:
    application = get_app()
    uvicorn.run(application)
