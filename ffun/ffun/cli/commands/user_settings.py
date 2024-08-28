import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.user_settings import domain as us_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_remove_deprecated_settings() -> None:
    async with with_app():
        await us_domain.remove_deprecated_settings()


@cli_app.command()
def remove_deprecated_settings() -> None:
    asyncio.run(run_remove_deprecated_settings())
