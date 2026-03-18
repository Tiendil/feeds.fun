import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.domain.entities import TagId
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.meta import domain as m_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_clean(chunk: int) -> None:
    async with with_app():
        logger.info("cleaning_started", chunk=chunk)

        logger.info("cleaning_orphaned_entries_started", chunk=chunk)

        while await m_domain.clean_orphaned_entries(chunk=chunk) != 0:
            pass

        logger.info("cleaning_orphaned_entries_finished")

        logger.info("cleaning_orphaned_feeds_started", chunk=chunk)

        while await m_domain.clean_orphaned_feeds(chunk=chunk) != 0:
            pass

        logger.info("cleaning_orphaned_feeds_finished")

        logger.info("cleaning_orphaned_tags_started", chunk=chunk)

        while await m_domain.clean_orphaned_tags(chunk=chunk) != 0:
            pass

        logger.info("cleaning_orphaned_tags_finished")

        logger.info("cleaning_finished")


@cli_app.command()  # type: ignore
def clean(chunk: int = 10000) -> None:
    asyncio.run(run_clean(chunk=chunk))


async def run_renormalize_tags(from_tag_id: int, to_tag_id: int) -> None:
    async with with_app():
        logger.info("renormalization_started", from_tag_id=from_tag_id, to_tag_id=to_tag_id)

        await m_domain.renormalize_tags(tag_ids=[TagId(tag_id) for tag_id in range(from_tag_id, to_tag_id + 1)])

        logger.info("renormalization_finished")


@cli_app.command()  # type: ignore
def renormalize_tags(from_tag_id: int, to_tag_id: int) -> None:
    asyncio.run(run_renormalize_tags(from_tag_id, to_tag_id))


async def run_shrink_feeds(chunk: int, log_every_n: int) -> None:
    async with with_app():
        logger.info("feeds_shrinking_started")

        counter = 0

        async for feed in f_domain.all_feeds_iterator(chunk=chunk):
            counter += 1

            if counter % log_every_n == 0:
                logger.info("shrinked_feeds", number=counter)

            await l_domain.shrink_feed(feed.id)

        logger.info("feeds_shrinking_finished")


@cli_app.command()  # type: ignore
def shrink_feeds(chunk: int = 1000, log_every_n: int = 1000) -> None:
    asyncio.run(run_shrink_feeds(chunk=chunk, log_every_n=log_every_n))
