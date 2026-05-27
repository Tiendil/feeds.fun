import datetime
from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, run_in_transaction
from ffun.domain import urls as d_urls
from ffun.domain.entities import EntryId, FeedId, UnknownUrl
from ffun.feeds import domain as f_domain
from ffun.library import operations
from ffun.library.entities import Entry, EntryChange, FeedEntryLink

logger = logging.get_module_logger()

catalog_entries = operations.catalog_entries
get_entries_by_ids = operations.get_entries_by_ids
get_entries_by_filter = operations.get_entries_by_filter
entries_in_period = operations.entries_in_period
entries_in_period_details = operations.entries_in_period_details
all_entries_iterator = operations.all_entries_iterator
get_entries_after_pointer = operations.get_entries_after_pointer
get_orphaned_entries = operations.get_orphaned_entries
count_total_entries = operations.count_total_entries
sync_orphaned_entries = operations.sync_orphaned_entries

_fallback_period = datetime.timedelta(days=365 * 100)


@run_in_transaction
async def get_feed_links_for_entries(
    execute: ExecuteType, entries_ids: Iterable[EntryId]
) -> dict[EntryId, list[FeedEntryLink]]:
    return await operations.get_feed_links_for_entries(execute, entries_ids)


@run_in_transaction
async def remove_entries_by_ids(execute: ExecuteType, entries_ids: Iterable[EntryId]) -> None:
    return await operations.remove_entries_by_ids(execute, entries_ids)


@run_in_transaction
async def unlink_all(execute: ExecuteType, feed_id: FeedId) -> set[EntryId]:
    return await operations.unlink_all(execute, feed_id)


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
    # TODO: since we constantly unlink entries from feeds
    #       doing anything based on feed_id (of any kind) looks like a not so good idea
    #       we should find some better solution.
    feed_id = feed_links[0].feed_id

    feed = await f_domain.get_feed(feed_id)

    new_external_url = d_urls.adjust_external_url(UnknownUrl(entry.external_url), feed.url)

    changes = []

    if new_external_url != entry.external_url:
        changes.append(
            EntryChange(id=entry.id, field="external_url", old_value=entry.external_url, new_value=new_external_url)
        )
        if apply and new_external_url is not None:
            await operations.update_external_url(entry.id, new_external_url)

    return changes


async def get_entries_by_filter_with_fallback(
    feeds_ids: list[FeedId], period: datetime.timedelta | None, limit: int, fallback_limit: int
) -> list[Entry]:

    entries = await get_entries_by_filter(feeds_ids=feeds_ids, period=period, limit=limit)

    if entries:
        return entries

    # if there is no news in requested interval try to get some older news
    entries = await get_entries_by_filter(feeds_ids=feeds_ids, period=_fallback_period, limit=fallback_limit)

    return entries


@run_in_transaction
async def shrink_feed(execute: ExecuteType, feed_id: FeedId) -> None:
    logger.info("shrinking_feed_started", feed_id=feed_id)

    removed_1 = await operations.unlink_feed_tail(execute, feed_id)
    removed_2 = await operations.unlink_old_entries(execute, feed_id)

    await operations.try_mark_as_orphanes(execute, removed_1 | removed_2)

    logger.info("shrinking_feed_finished", feed_id=feed_id)
