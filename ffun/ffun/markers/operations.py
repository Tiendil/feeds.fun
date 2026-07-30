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


async def set_marker(user_ids: Iterable[UserId | None], marker: Marker, entry_id: EntryId) -> None:
    user_ids = list(user_ids)

    if not user_ids:
        return

    sql = """
        INSERT INTO m_markers (id, user_id, marker, entry_id)
        SELECT requested.id, requested.user_id, %(marker)s, %(entry_id)s
        FROM UNNEST(%(ids)s::uuid[], %(user_ids)s::uuid[]) AS requested(id, user_id)
        ON CONFLICT DO NOTHING
        RETURNING user_id
    """

    results = await execute(
        sql,
        {
            "ids": [uuid.uuid4() for _ in user_ids],
            "user_ids": user_ids,
            "marker": marker,
            "entry_id": entry_id,
        },
    )

    for row in results:
        log_business_event("marker_set", user_id=row["user_id"], marker=marker, entry_id=entry_id)


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
