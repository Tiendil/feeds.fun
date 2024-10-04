import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.meta.domain import clean_orphaned_entries

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_clean(chunk: int) -> None:
    async with with_app():
        await clean_orphaned_entries(chunk=chunk)


@cli_app.command()
def clean(chunk: int = 1000) -> None:
    asyncio.run(run_clean(chunk=chunk))
