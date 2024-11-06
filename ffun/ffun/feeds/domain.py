from ffun.domain.entities import FeedId
from ffun.feeds import errors, operations
from ffun.feeds.entities import Feed

save_feed = operations.save_feed
update_feed_info = operations.update_feed_info
get_next_feeds_to_load = operations.get_next_feeds_to_load
mark_feed_as_loaded = operations.mark_feed_as_loaded
mark_feed_as_failed = operations.mark_feed_as_failed
mark_feed_as_orphaned = operations.mark_feed_as_orphaned
get_feeds = operations.get_feeds
get_source_ids = operations.get_source_ids
tech_remove_feed = operations.tech_remove_feed
count_total_feeds = operations.count_total_feeds
count_total_feeds_per_state = operations.count_total_feeds_per_state
count_total_feeds_per_last_error = operations.count_total_feeds_per_last_error


async def save_feeds(feeds: list[Feed]) -> list[FeedId]:
    real_ids = []

    for feed in feeds:
        real_ids.append(await save_feed(feed))

    return real_ids


async def get_feed(feed_id: FeedId) -> Feed:
    feeds = await get_feeds([feed_id])

    if not feeds:
        raise errors.NoFeedFound(feed_id=feed_id)

    return feeds[0]
