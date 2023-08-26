import uuid
from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.markers.entities import Marker

logger = logging.get_module_logger()


async def set_marker(user_id: uuid.UUID, marker: Marker, entry_id: uuid.UUID) -> None:
    sql = """
        INSERT INTO m_markers (id, user_id, marker, entry_id)
        VALUES (%(id)s, %(user_id)s, %(marker)s, %(entry_id)s)
        ON CONFLICT (user_id, marker, entry_id) DO NOTHING
    """

    await execute(sql, {"id": uuid.uuid4(), "user_id": user_id, "marker": marker, "entry_id": entry_id})


async def remove_marker(user_id: uuid.UUID, marker: Marker, entry_id: uuid.UUID) -> None:
    sql = """
        DELETE FROM m_markers
        WHERE user_id = %(user_id)s AND marker = %(marker)s AND entry_id = %(entry_id)s
    """

    await execute(sql, {"user_id": user_id, "marker": marker, "entry_id": entry_id})


async def get_markers(user_id: uuid.UUID, entries_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, set[Marker]]:
    sql = """
        SELECT entry_id, marker
        FROM m_markers
        WHERE user_id = %(user_id)s AND entry_id = ANY(%(entries_ids)s)
    """

    results = await execute(sql, {"user_id": user_id, "entries_ids": entries_ids})

    result: dict[uuid.UUID, set[Marker]] = {}

    for row in results:
        entry_id = row["entry_id"]
        marker = Marker(row["marker"])

        if entry_id not in result:
            result[entry_id] = set()

        result[entry_id].add(marker)

    return result
