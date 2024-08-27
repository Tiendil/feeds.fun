import uuid

from ffun.feeds import errors, operations
from ffun.feeds.entities import Feed, FeedId

save_feed = operations.save_feed
update_feed_info = operations.update_feed_info
get_next_feeds_to_load = operations.get_next_feeds_to_load
mark_feed_as_loaded = operations.mark_feed_as_loaded
mark_feed_as_failed = operations.mark_feed_as_failed
mark_feed_as_orphaned = operations.mark_feed_as_orphaned
get_feeds = operations.get_feeds
tech_remove_feed = operations.tech_remove_feed


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


def new_feed_id() -> FeedId:
    return FeedId(uuid.uuid4())
