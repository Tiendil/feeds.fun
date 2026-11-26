import datetime

from ffun.core.utils import zero_timestamp
from ffun.domain.entities import AbsoluteUrl, FeedUrl, ResourceUrl
from ffun.domain.urls import url_to_uid
from ffun.parsers.entities import EntryInfo, FeedInfo


class EntryBuilder:
    """Collect the first value received for each field of one entry."""

    __slots__ = ("_url", "_title", "_body", "_published_at")

    def __init__(self, url: AbsoluteUrl) -> None:
        self._url = url
        self._title: str | None = None
        self._body: str | None = None
        self._published_at: datetime.datetime | None = None

    @property
    def published_at(self) -> datetime.datetime | None:
        return self._published_at

    def add_title(self, title: str) -> None:
        if self._title is None:
            self._title = title

    def add_body(self, body: str) -> None:
        if self._body is None:
            self._body = body

    def add_published_at(self, published_at: datetime.datetime) -> None:
        if self._published_at is not None:
            return
        if published_at.utcoffset() is None:
            raise ValueError("Entry publication time must include a timezone")
        self._published_at = published_at

    def build(self) -> EntryInfo | None:
        if self._title is None:
            return None

        return EntryInfo(
            title=self._title,
            body=self._body or "",
            external_id=self._url,
            external_url=self._url,
            external_tags=set(),
            published_at=self._published_at or zero_timestamp(),
            references=[],
        )


class FeedBuilder:
    """Collect feed fields and assemble entries by URL."""

    __slots__ = ("url", "_title", "_description", "_site_url", "_entries")

    def __init__(self, url: ResourceUrl) -> None:
        self.url = url
        self._title: str | None = None
        self._description: str | None = None
        self._site_url: AbsoluteUrl | None = None
        self._entries: dict[AbsoluteUrl, EntryBuilder] = {}

    def add_title(self, title: str) -> None:
        if self._title is None:
            self._title = title

    def add_description(self, description: str) -> None:
        if self._description is None:
            self._description = description

    def add_site_url(self, site_url: AbsoluteUrl) -> None:
        if self._site_url is None:
            self._site_url = site_url

    def get_or_create(self, url: AbsoluteUrl) -> EntryBuilder:
        """Return the entry builder for this URL, creating it on first access."""
        entry = self._entries.get(url)
        if entry is None:
            entry = EntryBuilder(url)
            self._entries[url] = entry
        return entry

    def build(self) -> FeedInfo:
        def publication_order(entry: EntryBuilder) -> tuple[bool, datetime.datetime]:
            published_at = entry.published_at
            return published_at is not None, published_at or zero_timestamp()

        entry_builders = sorted(self._entries.values(), key=publication_order, reverse=True)
        return FeedInfo(
            url=FeedUrl(self.url),
            uid=url_to_uid(self.url),
            title=self._title or "",
            description=self._description or "",
            site_url=self._site_url,
            entries=[entry for builder in entry_builders if (entry := builder.build()) is not None],
        )
