import asyncio

import typer
from ffun.application.application import with_app

app = typer.Typer()


async def run_experiment(url: str) -> None:
    pass


@app.command()
def experiment(url: str) -> None:
    asyncio.run(run_experiment(url=url))
