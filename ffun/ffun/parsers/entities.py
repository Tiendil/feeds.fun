import datetime

import pydantic

from ffun.domain.entities import AbsoluteUrl, EntryId, FeedUrl, SourceId, UrlUid
from ffun.library.entities import CollectedEntry, Reference


class EntryInfo(pydantic.BaseModel):
    title: str
    body: str
    external_id: str
    external_url: AbsoluteUrl
    external_tags: set[str]
    published_at: datetime.datetime

    references: list[Reference]

    def log_info(self) -> dict[str, object]:
        return {"title": self.title, "external_url": self.external_url}

    # TODO: tests
    def to_collected_entry(self, entry_id: EntryId, source_id: SourceId) -> "CollectedEntry":
        return CollectedEntry(
            id=entry_id,
            source_id=source_id,
            title=self.title,
            body=self.body,
            external_id=self.external_id,
            external_url=self.external_url,
            external_tags=self.external_tags,
            published_at=self.published_at,
            references=self.references,
        )


class FeedInfo(pydantic.BaseModel):
    url: FeedUrl
    title: str
    description: str
    uid: UrlUid

    entries: list[EntryInfo]

    def log_info(self) -> dict[str, object]:
        return {"title": self.title, "url": self.url}
