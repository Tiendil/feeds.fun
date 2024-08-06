import asyncio
import uuid
import pathlib

from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.core import logging
from ffun.meta import domain as m_domain

logger = logging.get_module_logger()


async def run(processor: int, test: str, knowlege_base: pathlib.Path) -> None:

    async with with_app():
        pass


@app.command()
def test(processor: int, test: str, knowlege_base: pathlib.Path) -> None:
    asyncio.run(run(processor, test, knowlege_base))
