import datetime
from typing import Iterable

from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId


async def update_cataloged_time(entries_ids: Iterable[EntryId], new_time: datetime.datetime) -> None:
    await execute(
        "UPDATE l_feeds_to_entries SET created_at = %(time_border)s WHERE entry_id = ANY(%(ids)s)",
        {
            "time_border": new_time,
            "ids": list(entries_ids),
        },
    )

    await execute(
        "UPDATE l_entries SET created_at = %(time_border)s WHERE id = ANY(%(ids)s)",
        {
            "time_border": new_time,
            "ids": list(entries_ids),
        },
    )
