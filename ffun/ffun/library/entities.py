import datetime
import enum
from typing import Any

from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId, FeedId, SourceId


class ProcessedState(int, enum.Enum):
    success = 1
    error = 2
    retry_later = 3


class Entry(BaseEntity):
    id: EntryId
    source_id: SourceId
    title: str
    body: str
    external_id: str
    external_url: str
    external_tags: set[str]
    published_at: datetime.datetime

    # TODO: we do not save this field to the database
    #       at the saving time it set to NOW()
    #       => a value that is set up on the loading time will be lost
    #       maybe, it will be a good idea to have a two separate classes:
    #       - LoadedEntry — only for loader
    #       - SavedEntry — for everyone else
    cataloged_at: datetime.datetime

    @property
    def age(self) -> datetime.timedelta:
        return utils.now() - self.published_at

    def log_info(self) -> dict[str, Any]:
        return {"id": self.id, "source_id": self.source_id, "title": self.title, "external_url": self.external_url}


class EntryChange(BaseEntity):
    id: EntryId
    field: str
    old_value: Any
    new_value: Any


class FeedEntryLink(BaseEntity):
    feed_id: FeedId
    entry_id: EntryId
    created_at: datetime.datetime
