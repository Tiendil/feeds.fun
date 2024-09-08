from typing import Iterable

import async_lru

from ffun.feeds import domain as f_domain
from ffun.feeds import errors as f_errors
from ffun.feeds.entities import FeedId
from ffun.feeds_collections.entities import Collection
from ffun.feeds_collections.predefines import predefines

_test_feeds_in_collections: set[FeedId] = set()


def get_collections() -> Iterable[Collection]:
    return predefines.keys()


def get_feeds_for_collecton(collection: Collection) -> set[str]:
    return predefines[collection]


# TODO: update collections code to cache all feed in collections first call
@async_lru.alru_cache()
async def is_feed_in_collections(feed_id: FeedId) -> bool:

    if feed_id in _test_feeds_in_collections:
        return True

    try:
        feed = await f_domain.get_feed(feed_id)
    except f_errors.NoFeedFound:
        return False

    for collection in get_collections():
        if feed.url in get_feeds_for_collecton(collection):
            return True

    return False


# TODO: test
# TODO: switch all mocks in tests to this function
def add_test_feed_to_collections(feed_id: FeedId) -> None:
    _test_feeds_in_collections.add(feed_id)
