import uuid

from ffun.domain.entities import CollectionId, EntryId, FeedId, RuleId, SourceId, UserId


def new_user_id() -> UserId:
    return UserId(uuid.uuid4())


def new_entry_id() -> EntryId:
    return EntryId(uuid.uuid4())


def new_feed_id() -> FeedId:
    return FeedId(uuid.uuid4())


def new_collection_id() -> CollectionId:
    return CollectionId(uuid.uuid4())


def new_source_id() -> SourceId:
    return SourceId(uuid.uuid4())


def new_rule_id() -> RuleId:
    return RuleId(uuid.uuid4())
