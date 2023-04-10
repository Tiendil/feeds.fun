import logging

import httpx
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.parsers.domain import parse_feed

logger = logging.getLogger(__name__)


async def process_feed(feed: Feed) -> None:

    logger.info("Loading feed %s", feed)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(feed.url, follow_redirects=True)
    except Exception:
        logging.exception('Error while loading feed %s', feed)
        await f_domain.mark_feed_as_failed(feed.id,
                                           state=FeedState.damaged,
                                           error=FeedError.network_unknown)
        return

    try:
        content = response.content.decode(response.encoding)
    except Exception:
        logging.exception('Error while loading feed %s', feed)
        await f_domain.mark_feed_as_failed(feed.id,
                                           state=FeedState.damaged,
                                           error=FeedError.parsing_encoding_error)
        return

    try:
        entries = parse_feed(feed.id, content)
    except Exception:
        logging.exception('Error while loading feed %s', feed)
        await f_domain.mark_feed_as_failed(feed.id,
                                           state=FeedState.damaged,
                                           error=FeedError.parsing_format_error)
        return

    # TODO: store only new entries
    await l_domain.catalog_entries(entries=entries)

    await f_domain.mark_feed_as_loaded(feed.id)

    logger.info("Loaded %s entries", len(entries))
