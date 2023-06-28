import asyncio

import typer
from ffun.application.application import with_app
from tabulate import tabulate

app = typer.Typer()


async def run_experiment() -> None:
    pass


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
