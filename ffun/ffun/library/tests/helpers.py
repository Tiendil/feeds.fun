import datetime
from typing import Iterable

from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId, FeedId


async def update_published_time(entries_ids: Iterable[EntryId], new_time: datetime.datetime) -> None:
    await execute(
        "UPDATE l_feeds_to_entries SET published_at = %(time_border)s WHERE entry_id = ANY(%(ids)s)",
        {  # type: ignore
            "time_border": new_time,
            "ids": list(entries_ids),  # type: ignore
        },
    )

    await execute(
        "UPDATE l_entries SET published_at = %(time_border)s WHERE id = ANY(%(ids)s)",
        {  # type: ignore
            "time_border": new_time,
            "ids": list(entries_ids),  # type: ignore
        },
    )


async def update_link_created_time(feed_id: FeedId, entry_id: EntryId, new_time: datetime.datetime) -> None:
    await execute(
        "UPDATE l_feeds_to_entries SET created_at = %(created_at)s WHERE feed_id = %(feed_id)s AND entry_id = %(entry_id)s",
        {  # type: ignore
            "created_at": new_time,
            "feed_id": feed_id,  # type: ignore
            "entry_id": entry_id,  # type: ignore
        },
    )


async def update_link_published_time(feed_id: FeedId, entry_id: EntryId, new_time: datetime.datetime) -> None:
    await execute(
        "UPDATE l_feeds_to_entries SET published_at = %(published_at)s WHERE feed_id = %(feed_id)s AND entry_id = %(entry_id)s",
        {  # type: ignore
            "published_at": new_time,
            "feed_id": feed_id,  # type: ignore
            "entry_id": entry_id,  # type: ignore
        },
    )
