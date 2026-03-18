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

    def log_info(self) -> dict[str, Any]:
        return {"id": self.id, "source_id": self.source_id, "title": self.title, "external_url": self.external_url}


class Entry(BaseEntry):
    published_at: datetime.datetime
    created_at: datetime.datetime

    @property
    def global_age(self) -> datetime.timedelta:
        # TODO: THAT MUST BE FIXED
        return utils.now() - self.published_at

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

    def personalized_entry(self, published_at: datetime.datetime | None) -> "PersonalizedEntry":
        return PersonalizedEntry(
            id=self.id,
            source_id=self.source_id,
            title=self.title,
            body=self.body,
            external_id=self.external_id,
            external_url=self.external_url,
            external_tags=self.external_tags,
            published_at=published_at,
        )


class CollectedEntry(BaseEntry):
    published_at: datetime.datetime

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


class PersonalizedEntry(BaseEntry):
    published_at: datetime.datetime | None


class EntryChange(BaseEntity):
    id: EntryId
    field: str
    old_value: Any
    new_value: Any


class FeedEntryLink(BaseEntity):
    feed_id: FeedId
    entry_id: EntryId
    created_at: datetime.datetime
    published_at: datetime.datetime
