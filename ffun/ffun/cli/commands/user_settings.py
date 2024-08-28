import asyncio
import pathlib

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.processors_quality import domain as pq_domain
from ffun.processors_quality.domain import diff_processor_results, display_diffs
from ffun.processors_quality.entities import ProcessorResult
from ffun.processors_quality.knowlege_base import KnowlegeBase

from ffun.user_settings import domain as us_domain
from ffun.application.user_settings import UserSettings

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_remove_deprecated_settings() -> None:
    async with with_app():
        await us_domain.remove_deprecated_settings(actual_kinds={int(setting) for setting in UserSettings})


@cli_app.command()
def remove_deprecated_settings() -> None:
    asyncio.run(run_remove_deprecated_settings())
