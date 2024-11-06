import asyncio

import typer

from ffun.cli.commands import cleaner  # noqa: F401
from ffun.cli.commands import metrics  # noqa: F401
from ffun.cli.commands import processors_quality  # noqa: F401
from ffun.cli.commands import user_settings  # noqa: F401

app = typer.Typer()


async def run_experiment() -> None:
    pass


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())


app.add_typer(processors_quality.cli_app, name="processors-quality")
app.add_typer(user_settings.cli_app, name="user-settings")
app.add_typer(cleaner.cli_app, name="cleaner")
app.add_typer(metrics.cli_app, name="metrics")
