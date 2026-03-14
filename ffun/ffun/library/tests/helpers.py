import datetime
from typing import Iterable

from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId
from ffun.library.entities import Entry


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


async def sort_entries_by_created_at(entries: list[Entry]) -> list[tuple[Entry, datetime.datetime]]:
    rows = await execute(
        "SELECT id, created_at FROM l_entries WHERE id = ANY(%(ids)s)",
        {"ids": [entry.id for entry in entries]},
    )
    created_at_by_id = {row["id"]: row["created_at"] for row in rows}

    return sorted(
        [(entry, created_at_by_id[entry.id]) for entry in entries],
        key=lambda item: (item[1], item[0].id),
    )
