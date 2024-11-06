import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.meta.domain import clean_orphaned_entries

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_system_wide(chunk: int) -> None:
    async with with_app():
        # TOTAL tags, total and by category
        # TOTAL feeds
        # TOTAL entries
        # TOTAL users
        pass


@cli_app.command()
def system_wide() -> None:
    asyncio.run(run_system_wide())


async def run_per_user(chunk: int) -> None:
    async with with_app():
        # TODO: rules per user
        # TODO: feeds per user: custom, collections, total
        # TODO: has api key: yes/no, active/inactive
        # TODO: money spent
        pass


@cli_app.command()
def per_user() -> None:
    asyncio.run(run_system_wide())
