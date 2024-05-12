import uuid

from ffun.core import postgresql
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.ontology import domain as o_domain


async def merge_feeds(feed_1_id: uuid.UUID, feed_2_id: uuid.UUID) -> None:
    "Merge feed_2 into feed_1, remove feed_2."

    all_entries = await l_domain.get_entries_by_filter(feeds_ids=[feed_1_id, feed_2_id],
                                                       limit=postgresql.MAX_INTEGER)

    feed_1_entries = {entry.external_id: entry for entry in all_entries if entry.feed_id == feed_1_id}
    feed_2_entries = {entry.external_id: entry for entry in all_entries if entry.feed_id == feed_2_id}

    # move missing entries from feed_2 to feed_1
    for external_id, entry in list(feed_2_entries.items()):
        if external_id in feed_1_entries:
            continue

        await l_domain.tech_move_entry(entry.id, feed_1_id)

        del feed_2_entries[external_id]

    # move tags from entries in feed_2 to entries in feed_1
    for entry_2 in feed_2_entries.values():
        entry_1 = feed_1_entries[entry_2.external_id]

        await o_domain.tech_copy_relations(entry_from_id=entry_2.id, entry_to_id=entry_1.id)

    await remove_feed(feed_2_id)


async def remove_feed(feed_id: uuid.UUID) -> None:
    "Remove feed and all related entries."

    all_entries = await l_domain.get_entries_by_filter(feeds_ids=[feed_id],
                                                       limit=postgresql.MAX_INTEGER)

    entries_ids = [entry.id for entry in all_entries]

    await o_domain.remove_relations_for_entries(entries_ids)
    await l_domain.tech_remove_entries_by_feed_id(feed_id)
    await f_domain.tech_remove_feed(feed_id)