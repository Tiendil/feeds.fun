import uuid
from typing import Iterable

from ffun.core import logging, postgresql
from ffun.feeds import domain as f_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.markers import domain as m_domain
from ffun.meta.settings import settings
from ffun.ontology import domain as o_domain

logger = logging.get_module_logger()


async def merge_feeds(feed_1_id: uuid.UUID, feed_2_id: uuid.UUID) -> None:
    """Merge feed_2 into feed_1, remove feed_2."""
    log = logger.bind(function="merge_feeds")

    log.info("start", feed_1_id=feed_1_id, feed_2_id=feed_2_id)

    all_entries = await l_domain.get_entries_by_filter(feeds_ids=[feed_1_id, feed_2_id], limit=postgresql.MAX_INTEGER)

    feed_1_entries = {entry.external_id: entry for entry in all_entries if entry.feed_id == feed_1_id}
    feed_2_entries = {entry.external_id: entry for entry in all_entries if entry.feed_id == feed_2_id}

    log.info("entries", feed_1=len(feed_1_entries), feed_2=len(feed_2_entries))

    # move missing entries from feed_2 to feed_1
    for external_id, entry in list(feed_2_entries.items()):
        log.info("process_entry", external_id=external_id, entry_id=entry.id)

        if external_id in feed_1_entries:
            log.info("entry_will_be_merged", entry_id=entry.id)
            continue

        log.info("move_entry", entry_id=entry.id)
        await l_domain.tech_move_entry(entry.id, feed_1_id)

        del feed_2_entries[external_id]

    log.info("merge_entries")

    # move tags from entries in feed_2 to entries in feed_1
    for entry_2 in feed_2_entries.values():
        entry_1 = feed_1_entries[entry_2.external_id]

        log.info("copy_relations", from_entry_id=entry_2.id, to_entry_id=entry_1.id)
        await o_domain.tech_copy_relations(entry_from_id=entry_2.id, entry_to_id=entry_1.id)

        log.info("merge_markers", from_entry_id=entry_2.id, to_entry_id=entry_1.id)
        await m_domain.tech_merge_markers(from_entry_id=entry_2.id, to_entry_id=entry_1.id)

    await fl_domain.tech_merge_feeds(from_feed_id=feed_2_id, to_feed_id=feed_1_id)

    await remove_feed(feed_2_id)


async def remove_feed(feed_id: uuid.UUID) -> None:
    """Remove feed and all related entries."""
    all_entries = await l_domain.get_entries_by_filter(feeds_ids=[feed_id], limit=postgresql.MAX_INTEGER)

    entries_ids = [entry.id for entry in all_entries]

    await remove_entries(entries_ids)

    await f_domain.tech_remove_feed(feed_id)


async def remove_entries(entries_ids: Iterable[uuid.UUID]) -> int:
    """Remove entries and all related markers and relations."""
    entries_to_remove = list(entries_ids)

    await m_domain.remove_markers_for_entries(entries_to_remove)
    await o_domain.remove_relations_for_entries(entries_to_remove)
    await l_domain.tech_remove_entries_by_ids(entries_to_remove)

    return len(entries_to_remove)


async def limit_entries_for_feed(feed_id: uuid.UUID, limit: int | None = None) -> None:
    """Remove oldest entries for feed to keep only `limit` entries."""
    if limit is None:
        limit = settings.max_entries_per_feed

    entries_to_remove = await l_domain.tech_get_feed_entries_tail(feed_id=feed_id, offset=limit)

    if not entries_to_remove:
        logger.info("feed_has_no_entries_tail", feed_id=feed_id, entries_limit=limit)
        return

    entries_removed = await remove_entries(entries_to_remove)

    logger.info("feed_entries_tail_removed", feed_id=feed_id, entries_limit=limit, entries_removed=entries_removed)
