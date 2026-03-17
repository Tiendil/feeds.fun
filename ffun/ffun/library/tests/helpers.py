import datetime
from typing import Iterable

from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId, FeedId


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
