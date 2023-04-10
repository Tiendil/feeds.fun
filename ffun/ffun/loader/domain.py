import logging

import httpx
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.library import domain as l_domain
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

    external_ids = [entry.external_id for entry in entries]

    stored_entries_external_ids  = await l_domain.check_stored_entries_by_external_ids(external_ids)

    entries_to_store = [entry for entry in entries
                        if entry.external_id not in stored_entries_external_ids]

    await l_domain.catalog_entries(entries=entries_to_store)

    await f_domain.mark_feed_as_loaded(feed.id)

    logger.info("Loaded %s entries, stored entries: %s", len(entries), len(entries_to_store))
