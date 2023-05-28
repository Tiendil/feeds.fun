import typer
import uvicorn
from ffun.application.application import get_app, prepare_app

from ..application import app


@app.command()
def server(api: bool = False,
           supertokens: bool = False) -> None:

    prepare_app(api=api,
                supertokens=supertokens)

    application = get_app()

    # TODO: move uvicorn out of here
    uvicorn.run(application, host="0.0.0.0")
