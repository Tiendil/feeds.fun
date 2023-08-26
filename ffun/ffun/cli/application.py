import asyncio

import typer

app = typer.Typer()


async def run_experiment() -> None:
    pass


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
