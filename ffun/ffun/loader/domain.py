import httpx
import structlog
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.library import domain as l_domain
from ffun.parsers.domain import parse_feed

logger = structlog.getLogger(__name__)


async def process_feed(feed: Feed) -> None:

    logger.info("Loading feed %s", feed)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(feed.url, follow_redirects=True)
    except Exception:
        logger.exception('error_while_loading_feed', feed=feed)
        await f_domain.mark_feed_as_failed(feed.id,
                                           state=FeedState.damaged,
                                           error=FeedError.network_unknown)
        return

    try:
        content = response.content.decode(response.encoding)
    except Exception:
        logger.exception('error_while_decoding_feed', feed=feed)
        await f_domain.mark_feed_as_failed(feed.id,
                                           state=FeedState.damaged,
                                           error=FeedError.parsing_encoding_error)
        return

    try:
        entries = parse_feed(feed.id, content)
    except Exception:
        logger.exception('error_while_parsing_feed', feed=feed)
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

    logger.info("entries_loaded", loaded_number=len(entries), stored_number=len(entries_to_store))
