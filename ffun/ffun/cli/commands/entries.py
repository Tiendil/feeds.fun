import asyncio

from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.core import logging
from ffun.library.domain import all_entries_iterator, normalize_entry

logger = logging.get_module_logger()


async def run(apply: bool, chunk: int, log_every_n: int) -> None:  # noqa: CCR001
    changes_counter = 0

    async with with_app():
        counter = 0

        async for entry in all_entries_iterator(chunk=chunk):
            counter += 1

            if counter % log_every_n == 0:
                logger.info("normalized_entries", number=counter)

            changes = await normalize_entry(entry, apply=apply)

            for change in changes:
                changes_counter += 1
                logger.info("change", number=changes_counter, change=change)

    logger.info("normalized_entries", number=counter)


@app.command()
def normalize_entries(apply: bool = False, chunk: int = 1000, log_every_n: int = 1000) -> None:
    asyncio.run(run(apply=apply, chunk=chunk, log_every_n=log_every_n))
