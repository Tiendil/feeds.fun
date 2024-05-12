import uuid
from typing import Any

from ffun.core import utils
from ffun.library import domain
from ffun.library.entities import Entry


def fake_url() -> str:
    return f"https://{uuid.uuid4().hex}.com"


def fake_title() -> str:
    return f"Entry Title: {uuid.uuid4().hex}"


def fake_body() -> str:
    return f"Entry Body: {uuid.uuid4().hex}"


def fake_entry(loaded_feed_id: uuid.UUID, **kwargs: Any) -> Entry:
    return Entry(
        id=uuid.uuid4() if "id" not in kwargs else kwargs["id"],
        feed_id=loaded_feed_id,
        title=fake_title() if "title" not in kwargs else kwargs["title"],
        body=fake_body() if "body" not in kwargs else kwargs["body"],
        external_id=uuid.uuid4().hex if "external_id" not in kwargs else kwargs["external_id"],
        external_url=fake_url() if "external_url" not in kwargs else kwargs["external_url"],
        external_tags={uuid.uuid4().hex, uuid.uuid4().hex},
        published_at=utils.now() if "published_at" not in kwargs else kwargs["published_at"],
        cataloged_at=utils.now() if "cataloged_at" not in kwargs else kwargs["cataloged_at"],
    )


async def n_entries(loaded_feed_id: uuid.UUID, n: int) -> dict[uuid.UUID, Entry]:
    new_entries = [fake_entry(loaded_feed_id) for _ in range(n)]
    await domain.catalog_entries(new_entries)
    return await domain.get_entries_by_ids([entry.id for entry in new_entries])  # type: ignore


async def n_entries_list(loaded_feed_id: uuid.UUID, n: int) -> list[Entry]:
    entries = await n_entries(loaded_feed_id, n)
    result = list(entries.values())

    result.sort(key=lambda entry: entry.cataloged_at, reverse=True)

    return result
