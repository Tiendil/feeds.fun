import asyncio

import typer
from tabulate import tabulate

from ffun.application.application import with_app


app = typer.Typer()


async def run_experiment() -> None:
    pass


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
