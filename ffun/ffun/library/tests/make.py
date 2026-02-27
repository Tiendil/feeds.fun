import datetime
import uuid

from ffun.core import utils
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import AbsoluteUrl, EntryId, SourceId
from ffun.domain.urls import str_to_absolute_url
from ffun.feeds.entities import Feed
from ffun.library import domain
from ffun.library.entities import Entry


def fake_url() -> str:
    return f"https://{uuid.uuid4().hex}.com"


def fake_title() -> str:
    return f"Entry Title: {uuid.uuid4().hex}"


def fake_body() -> str:
    return f"Entry Body: {uuid.uuid4().hex}"


def fake_entry(
    source_id: SourceId,
    *,
    id: uuid.UUID | None = None,
    title: str | None = None,
    body: str | None = None,
    external_id: str | None = None,
    external_url: AbsoluteUrl | str | None = None,
    external_tags: set[str] | None = None,
    published_at: datetime.datetime | None = None,
    cataloged_at: datetime.datetime | None = None,
) -> Entry:
    resolved_external_url = fake_url() if external_url is None else external_url

    return Entry(
        id=new_entry_id() if id is None else id,
        source_id=source_id,
        title=fake_title() if title is None else title,
        body=fake_body() if body is None else body,
        external_id=uuid.uuid4().hex if external_id is None else external_id,
        external_url=str_to_absolute_url(resolved_external_url),
        external_tags={uuid.uuid4().hex, uuid.uuid4().hex} if external_tags is None else external_tags,
        published_at=utils.now() if published_at is None else published_at,
        cataloged_at=utils.now() if cataloged_at is None else cataloged_at,
    )


async def n_entries(feed: Feed, n: int) -> dict[EntryId, Entry]:
    new_entries = [fake_entry(feed.source_id) for _ in range(n)]
    await domain.catalog_entries(feed.id, new_entries)
    return await domain.get_entries_by_ids([entry.id for entry in new_entries])  # type: ignore


async def n_entries_list(feed: Feed, n: int) -> list[Entry]:
    entries = await n_entries(feed, n)

    result = list(entries.values())

    # from newest to oldest
    result.sort(key=lambda entry: entry.cataloged_at, reverse=True)

    return result
