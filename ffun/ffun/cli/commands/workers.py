import asyncio

import typer
from ffun.application.application import prepare_app, with_app

from ..application import app


async def run(loader: bool,
              librarian: bool) -> None:

    prepare_app(loader=loader,
                librarian=librarian)

    async with with_app(loader=loader,
                        librarian=librarian) as fastapi_app:
        while True:
            await asyncio.sleep(0.1)


@app.command()
def workers(loader: bool = False,
            librarian: bool = False) -> None:

    asyncio.run(run(loader=loader,
                    librarian=librarian))
