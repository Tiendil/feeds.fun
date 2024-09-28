import uuid

from ffun.domain.entities import FeedId, EntryId, CollectionId


def new_entry_id() -> EntryId:
    return EntryId(uuid.uuid4())


def new_feed_id() -> FeedId:
    return FeedId(uuid.uuid4())


def new_collection_id() -> CollectionId:
    return CollectionId(uuid.uuid4())
