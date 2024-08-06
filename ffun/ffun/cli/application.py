import asyncio
from ffun.cli.commands import processors_quality  # noqa: F401

import typer

app = typer.Typer()


async def run_experiment() -> None:
    pass


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())


app.add_typer(processors_quality.cli_app, name="processors-quality")
