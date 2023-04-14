import asyncio

import typer
import uvicorn
from ffun.application.application import with_app

app = typer.Typer()


# TODO: cleanup
async def run_experiment() -> None:
    async with with_app():
        # add temporary code here
        pass


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
