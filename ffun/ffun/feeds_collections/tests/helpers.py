from ffun.domain.entities import CollectionId, FeedId
from ffun.feeds_collections.collections import collections


async def add_feed_to_collection(collection_id: CollectionId, feed_id: FeedId) -> None:
    await collections.add_test_feed_to_collections(collection_id, feed_id)
