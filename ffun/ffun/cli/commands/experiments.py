import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.meta.domain import clean_orphaned_entries

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_experiment() -> None:
    async with with_app():
        print("Running experiment")


@cli_app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
