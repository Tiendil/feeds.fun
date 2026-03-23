import datetime
import enum
from typing import Any

from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import AbsoluteUrl, EntryId, FeedId, SourceId


class ProcessedState(int, enum.Enum):
    success = 1
    error = 2
    retry_later = 3


class BaseEntry(BaseEntity):
    id: EntryId
    source_id: SourceId
    title: str
    body: str
    external_id: str
    external_url: AbsoluteUrl
    external_tags: set[str]
    published_at: datetime.datetime

    def log_info(self) -> dict[str, Any]:
        return {"id": self.id, "source_id": self.source_id, "title": self.title, "external_url": self.external_url}


class Entry(BaseEntry):
    created_at: datetime.datetime

    @property
    def published_at_for_processing(self) -> datetime.datetime:
        """Entry published_at that is used to determine whether the entry is too old for processing.

        We use the smart algorithm to determine the "real" published_at value
        because an actual third-party published_at is absolutely unreliable.

        Such behavior is required to reduce siturations when the user adds a new feed source,
        and all entries from it is treated as published "now", which leads to spending
        tokens on processing old entries, that normally shouldn't be processed.

        The logic is the following.

        Assumptions/expectations from other code:

        - If the feed source has no published_at, it will be set equal to created_at
          at the moment of entry creation.

        Algorithm:

        1. If published_at looks broken (start of epoch, datetime.min, etc.), we use created_at as published_at.
        2. If published_at is in the future (relative to created_at), we use created_at as published_at.
        3. Otherwise, we use published_at as is.
        """
        assert self.published_at.tzinfo is not None and self.published_at.utcoffset() is not None
        assert self.created_at.tzinfo is not None and self.created_at.utcoffset() is not None

        if self.published_at == datetime.datetime.min.replace(tzinfo=datetime.UTC):
            return self.created_at

        if self.published_at == utils.zero_timestamp():
            return self.created_at

        if self.published_at > self.created_at:
            return self.created_at

        return self.published_at

    @property
    def age_for_processing(self) -> datetime.timedelta:
        return utils.now() - self.published_at_for_processing

    def collected_entry(self) -> "CollectedEntry":
        return CollectedEntry(
            id=self.id,
            source_id=self.source_id,
            title=self.title,
            body=self.body,
            external_id=self.external_id,
            external_url=self.external_url,
            external_tags=self.external_tags,
            published_at=self.published_at,
        )


class CollectedEntry(BaseEntry):
    def fake_entry(self, created_at: datetime.datetime) -> Entry:
        return Entry(
            id=self.id,
            source_id=self.source_id,
            title=self.title,
            body=self.body,
            external_id=self.external_id,
            external_url=self.external_url,
            external_tags=self.external_tags,
            published_at=self.published_at,
            created_at=created_at,
        )


class EntryChange(BaseEntity):
    id: EntryId
    field: str
    old_value: Any
    new_value: Any


class FeedEntryLink(BaseEntity):
    feed_id: FeedId
    entry_id: EntryId
    created_at: datetime.datetime
