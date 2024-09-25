import uuid

from ffun.feeds_collections.entities import CollectionId


def new_collection_id() -> CollectionId:
    return CollectionId(uuid.uuid4())
