import asyncio
import uuid

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.domain.entities import CollectionId, FeedUrl, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url
from ffun.feeds_collections.collections import collections
from ffun.loader.domain import extract_feed_info

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def _estimate_entries_per_day(feed_url: FeedUrl) -> float | None:
    logger.info("start_feed_extraction", feed_url=feed_url)

    feed_info = await extract_feed_info(feed_id=None, feed_url=feed_url)

    if feed_info is None:
        logger.info("feed_extraction_failed", feed_url=feed_url)
        return None

    if not feed_info.entries:
        logger.info("feed_has_no_entries", feed_url=feed_url)
        return None

    if len(feed_info.entries) == 1:
        logger.info("feed_has_only_one_entry", feed_url=feed_url)
        return None

    min_published_at = min(entry.published_at for entry in feed_info.entries)
    max_published_at = max(entry.published_at for entry in feed_info.entries)

    entries_per_day = len(feed_info.entries) / (max_published_at - min_published_at).total_seconds() * 86400

    logger.info("estimated_entries_for_feed_in_day", feed_url=feed_url, entries_per_day=entries_per_day)

    return entries_per_day


async def run_entries_per_day_for_feed(raw_feed_url: str) -> None:
    async with with_app():
        feed_url = normalize_classic_unknown_url(UnknownUrl(raw_feed_url))

        assert feed_url is not None

        entries_per_day = await _estimate_entries_per_day(to_feed_url(feed_url))

        logger.info("estimated_entries_for_feed_in_day", feed_url=feed_url, entries_per_day=entries_per_day)


async def run_entries_per_day_for_collection(collection_id: uuid.UUID) -> None:
    async with with_app():
        logger.info("start_collection_extraction", collection_id=collection_id)

        collection = collections.collection(CollectionId(collection_id))

        urls = {feed_info.url for feed_info in collection.feeds}

        total_entries_per_day = 0.0

        for url in urls:
            entries_per_day = await _estimate_entries_per_day(url)

            if entries_per_day is not None:
                total_entries_per_day += entries_per_day

        logger.info(
            "estimated_entries_for_feed_in_day", collection_id=collection_id, entries_per_day=total_entries_per_day
        )


@cli_app.command()
def entries_per_day_for_feed(feed_url: str) -> None:
    asyncio.run(run_entries_per_day_for_feed(feed_url))


@cli_app.command()
def entries_per_day_for_collection(collection_id: uuid.UUID) -> None:
    asyncio.run(run_entries_per_day_for_collection(collection_id))
