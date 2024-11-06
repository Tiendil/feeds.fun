from ffun.domain import urls as d_urls
from ffun.domain.entities import EntryId, FeedId
from ffun.feeds import domain as f_domain
from ffun.library import operations
from ffun.library.entities import Entry, EntryChange

catalog_entries = operations.catalog_entries
get_entries_by_ids = operations.get_entries_by_ids
get_entries_by_filter = operations.get_entries_by_filter
find_stored_entries_for_feed = operations.find_stored_entries_for_feed
all_entries_iterator = operations.all_entries_iterator
get_entries_after_pointer = operations.get_entries_after_pointer
unlink_feed_tail = operations.unlink_feed_tail
get_feed_links_for_entries = operations.get_feed_links_for_entries
get_orphaned_entries = operations.get_orphaned_entries
remove_entries_by_ids = operations.remove_entries_by_ids
count_total_entries = operations.count_total_entries


async def get_entry(entry_id: EntryId) -> Entry:
    entries = await get_entries_by_ids([entry_id])
    found_entry = entries.get(entry_id)
    assert found_entry is not None
    return found_entry


async def get_feeds_for_entry(entry_id: EntryId) -> set[FeedId]:
    mapping = await get_feed_links_for_entries([entry_id])

    if not mapping:
        return set()

    return {link.feed_id for link in mapping[entry_id]}


async def normalize_entry(entry: Entry, apply: bool = False) -> list[EntryChange]:
    feed_links_mapping = await get_feed_links_for_entries([entry.id])

    if entry.id not in feed_links_mapping:
        return []

    feed_links = feed_links_mapping[entry.id]

    feed_links.sort(key=lambda link: link.created_at)

    # use oldest link to chose normalization feed
    # TODO: give priority to feeds from collections
    feed_id = feed_links[0].feed_id

    feed = await f_domain.get_feed(feed_id)

    new_external_url = d_urls.normalize_external_url(entry.external_url, feed.url)

    changes = []

    if new_external_url != entry.external_url:
        changes.append(
            EntryChange(id=entry.id, field="external_url", old_value=entry.external_url, new_value=new_external_url)
        )
        if apply and new_external_url is not None:
            await operations.update_external_url(entry.id, new_external_url)

    return changes
