import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.entities import UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, url_to_source_uid, url_to_uid
from ffun.library.operations import all_entries_iterator, count_total_entries
from ffun.loader.domain import extract_feed_info

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_entries_per_day_for_feed(feed_url: str) -> None:
    async with with_app():
        logger.info("start_feed_extraction", feed_url=feed_url)

        feed_info = await extract_feed_info(feed_id=None, feed_url=feed_url)

        if feed_info is None:
            logger.info("feed_extraction_failed", feed_url=feed_url)
            return

        if not feed_info.entries:
            logger.info("feed_has_no_entries", feed_url=feed_url)
            return

        if len(feed_info.entries) == 1:
            logger.info("feed_has_only_one_entry", feed_url=feed_url)
            return

        min_published_at = min(entry.published_at for entry in feed_info.entries)
        max_published_at = max(entry.published_at for entry in feed_info.entries)

        entries_per_day = len(feed_info.entries) / (max_published_at - min_published_at).total_seconds() * 86400

        logger.info('estimated_entries_for_feed_in_day', feed_url=feed_url, entries_per_day=entries_per_day)


@cli_app.command()
def entries_per_day_for_feed(feed_url: str) -> None:
    asyncio.run(run_entries_per_day_for_feed(feed_url))
