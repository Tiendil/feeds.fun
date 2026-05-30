from ffun.domain.entities import CollectionId, CollectionSlug, FeedId
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import Collection


def collection(collection_id: CollectionId) -> Collection:
    return collections.collection(collection_id)


def collection_by_slug(slug: CollectionSlug) -> Collection:
    return collections.collection_by_slug(slug)


def all_collections() -> list[Collection]:
    return collections.collections()


def collections_for_feed(feed_id: FeedId) -> list[CollectionId]:
    return collections.collections_for_feed(feed_id)
