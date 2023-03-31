
import asyncio
import logging
import pathlib

from ffun.application.application import with_app
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed
from ffun.library import domain as l_domain
from ffun.loader import domain as load_domain

from ..application import app

logger = logging.getLogger(__name__)


async def run(number: int) -> None:
    async with with_app():
        feeds = await f_domain.get_next_feeds_to_load(number=number)

        for feed in feeds:
            logger.info("Loading feed %s", feed)
            entries = await load_domain.load_feed(feed=feed)
            await l_domain.catalog_entries(entries=entries)
            await f_domain.mark_feed_as_loaded(feed.id)
            logger.info("Loaded %s entries", len(entries))


@app.command()
def load_feeds(number: int = 1) -> None:
    asyncio.run(run(number=number))
