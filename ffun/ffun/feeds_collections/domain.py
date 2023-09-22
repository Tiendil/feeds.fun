import uuid
from typing import Iterable

import async_lru

from ffun.feeds import domain as f_domain
from ffun.feeds import errors as f_errors
from ffun.feeds_collections.entities import Collection
from ffun.feeds_collections.predefines import predefines


def get_collections() -> Iterable[Collection]:
    return predefines.keys()


def get_feeds_for_collecton(collection: Collection) -> set[str]:
    return predefines[collection]


@async_lru.alru_cache()
async def is_feed_in_collections(feed_id: uuid.UUID) -> bool:
    try:
        feed = await f_domain.get_feed(feed_id)
    except f_errors.NoFeedFound:
        return False

    for collection in get_collections():
        if feed.url in get_feeds_for_collecton(collection):
            return True

    return False
