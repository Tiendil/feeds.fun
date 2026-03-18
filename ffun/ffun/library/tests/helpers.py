import datetime
from typing import Iterable

from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId, FeedId
from ffun.library.operations import try_mark_as_orphanes


async def update_link_created_time(feed_id: FeedId, entry_id: EntryId, new_time: datetime.datetime) -> None:
    await execute(
        (
            "UPDATE l_feeds_to_entries SET created_at = %(created_at)s "
            "WHERE feed_id = %(feed_id)s AND entry_id = %(entry_id)s"
        ),
        {  # type: ignore
            "created_at": new_time,
            "feed_id": feed_id,
            "entry_id": entry_id,
        },
    )


async def update_links_created_time(
    feed_id: FeedId, entries_ids: Iterable[EntryId], new_time: datetime.datetime
) -> None:
    for entry_id in entries_ids:
        await update_link_created_time(feed_id, entry_id, new_time)


async def update_entry_created_time(entries_ids: Iterable[EntryId], new_time: datetime.datetime) -> None:
    entry_ids = list(entries_ids)

    if not entry_ids:
        return

    await execute(
        "UPDATE l_entries SET created_at = %(created_at)s WHERE id = ANY(%(entry_ids)s)",
        {"created_at": new_time, "entry_ids": entry_ids},  # type: ignore
    )
    await execute(
        "UPDATE l_feeds_to_entries SET entry_created_at = %(entry_created_at)s WHERE entry_id = ANY(%(entry_ids)s)",
        {"entry_created_at": new_time, "entry_ids": entry_ids},  # type: ignore
    )


async def unlink_entries_from_feed(feed_id: FeedId, entry_ids: Iterable[EntryId]) -> None:
    entries_ids = list(entry_ids)

    if not entries_ids:
        return

    await execute(
        "DELETE FROM l_feeds_to_entries WHERE feed_id = %(feed_id)s AND entry_id = ANY(%(entry_ids)s)",
        {"feed_id": feed_id, "entry_ids": entries_ids},  # type: ignore
    )
    await try_mark_as_orphanes(execute, entries_ids)
