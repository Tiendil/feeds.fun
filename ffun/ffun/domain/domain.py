import uuid

from ffun.domain.entities import CollectionId, EntryId, FeedId, SourceId


def new_entry_id() -> EntryId:
    return EntryId(uuid.uuid4())


def new_feed_id() -> FeedId:
    return FeedId(uuid.uuid4())


def new_collection_id() -> CollectionId:
    return CollectionId(uuid.uuid4())


def new_source_id() -> SourceId:
    return SourceId(uuid.uuid4())
