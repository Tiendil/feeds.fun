import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.domain.entities import TagId
from ffun.meta.domain import clean_orphaned_entries, clean_orphaned_feeds, clean_orphaned_tags
from ffun.meta.domain import renormalize_tags as meta_renormalize_tags

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

        logger.info("cleaning_orphaned_tags_started", chunk=chunk)

        while await clean_orphaned_tags(chunk=chunk) != 0:
            pass

        logger.info("cleaning_orphaned_tags_finished")

        logger.info("cleaning_finished")


@cli_app.command()
def clean(chunk: int = 10000) -> None:
    asyncio.run(run_clean(chunk=chunk))


async def run_renormalize_tags(from_tag_id: int, to_tag_id: int) -> None:
    async with with_app():
        logger.info("renormalization_started", from_tag_id=from_tag_id, to_tag_id=to_tag_id)

        await meta_renormalize_tags(tag_ids=[TagId(tag_id) for tag_id in range(from_tag_id, to_tag_id + 1)])

        logger.info("renormalization_finished")


@cli_app.command()
def renormalize_tags(from_tag_id: int, to_tag_id: int) -> None:
    asyncio.run(run_renormalize_tags(from_tag_id, to_tag_id))
