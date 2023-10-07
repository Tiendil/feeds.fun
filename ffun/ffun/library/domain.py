import uuid

from ffun.domain import urls as d_urls
from ffun.feeds import domain as f_domain
from ffun.library import operations
from ffun.library.entities import Entry

catalog_entries = operations.catalog_entries
get_entries_by_ids = operations.get_entries_by_ids
get_entries_by_filter = operations.get_entries_by_filter
get_new_entries = operations.get_new_entries
check_stored_entries_by_external_ids = operations.check_stored_entries_by_external_ids
mark_entry_as_processed = operations.mark_entry_as_processed
get_entries_to_process = operations.get_entries_to_process


async def get_entry(entry_id: uuid.UUID) -> Entry:
    entries = await get_entries_by_ids([entry_id])
    found_entry = entries.get(entry_id)
    assert found_entry is not None
    return found_entry


async def normalize_entry(entry: Entry) -> None:

    feed = await f_domain.get_feed(entry.feed_id)

    new_external_url = d_urls.normalize_external_url(entry.external_url, feed.url)

    if new_external_url != entry.external_url:
        await operations.update_external_url(entry.id, new_external_url)
