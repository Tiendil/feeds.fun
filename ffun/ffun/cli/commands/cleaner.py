import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.meta.domain import clean_orphaned_entries, clean_orphaned_feeds

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_clean(chunk: int) -> None:
    async with with_app():
        logger.info("cleaning_started", chunk=chunk)

        logger.info("cleaning_orphaned_entries_started", chunk=chunk)

        while await clean_orphaned_entries(chunk=chunk) != 0:
            pass

        logger.info("cleaning_orphaned_entries_finished")

        logger.info("cleaning_orphaned_feeds_started", chunk=chunk)

        while await clean_orphaned_feeds(chunk=chunk) != 0:
            pass

        logger.info("cleaning_orphaned_feeds_finished")

        logger.info("cleaning_finished")


@cli_app.command()
def clean(chunk: int = 10000) -> None:
    asyncio.run(run_clean(chunk=chunk))
