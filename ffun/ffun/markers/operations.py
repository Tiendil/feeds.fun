import uuid
from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId, UserId
from ffun.markers.entities import Marker
from ffun.markers.settings import settings

logger = logging.get_module_logger()


def log_business_event(event: str, user_id: UserId | None, marker: Marker, entry_id: EntryId) -> None:
    if marker not in settings.log_business_events_for:
        return

    logger.business_event(event, user_id=user_id, marker=marker, entry_id=entry_id)


async def set_marker(user_id: UserId | None, marker: Marker, entry_id: EntryId) -> None:
    if user_id is None:
        sql = """
            INSERT INTO m_markers (id, user_id, marker, entry_id)
            VALUES (%(id)s, %(user_id)s, %(marker)s, %(entry_id)s)
            ON CONFLICT (entry_id, marker) WHERE user_id IS NULL DO NOTHING
            RETURNING id
        """
    else:
        sql = """
            INSERT INTO m_markers (id, user_id, marker, entry_id)
            VALUES (%(id)s, %(user_id)s, %(marker)s, %(entry_id)s)
            ON CONFLICT (user_id, entry_id, marker) WHERE user_id IS NOT NULL DO NOTHING
            RETURNING id
        """

    results = await execute(sql, {"id": uuid.uuid4(), "user_id": user_id, "marker": marker, "entry_id": entry_id})

    if results:
        log_business_event("marker_set", user_id=user_id, marker=marker, entry_id=entry_id)


async def remove_marker(user_id: UserId | None, marker: Marker, entry_id: EntryId) -> None:
    sql = """
        DELETE FROM m_markers
        WHERE user_id IS NOT DISTINCT FROM %(user_id)s AND marker = %(marker)s AND entry_id = %(entry_id)s
        RETURNING id
    """

    results = await execute(sql, {"user_id": user_id, "marker": marker, "entry_id": entry_id})

    if results:
        log_business_event("marker_removed", user_id=user_id, marker=marker, entry_id=entry_id)


async def get_markers(user_id: UserId | None, entries_ids: Iterable[EntryId]) -> dict[EntryId, set[Marker]]:
    entries_ids = list(entries_ids)

    if user_id is None:
        sql = """
            SELECT entry_id, marker
            FROM m_markers
            WHERE user_id IS NULL AND entry_id = ANY(%(entries_ids)s)
        """
    else:
        sql = """
            SELECT entry_id, marker
            FROM m_markers
            WHERE (user_id = %(user_id)s OR user_id IS NULL) AND entry_id = ANY(%(entries_ids)s)
        """

    results = await execute(sql, {"user_id": user_id, "entries_ids": entries_ids})

    result: dict[EntryId, set[Marker]] = {}

    for row in results:
        entry_id = row["entry_id"]
        marker = Marker(row["marker"])

        if entry_id not in result:
            result[entry_id] = set()

        result[entry_id].add(marker)

    return result


async def remove_markers_for_entries(entries_ids: Iterable[EntryId]) -> None:
    sql = """
        DELETE FROM m_markers
        WHERE entry_id = ANY(%(entries_ids)s)
    """

    await execute(sql, {"entries_ids": list(entries_ids)})
