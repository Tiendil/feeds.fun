from typing import Iterable

from pypika import PostgreSQLQuery

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import EntryId, ProcessorId

logger = logging.get_module_logger()


async def add_entries_to_failed_storage(processor_id: ProcessorId, entry_ids: Iterable[EntryId]) -> None:
    query = PostgreSQLQuery.into("ln_failed_entries").columns("processor_id", "entry_id")

    for entry_id in entry_ids:
        query = query.insert(processor_id, entry_id)

    await execute(str(query))


async def get_failed_entries(execute: ExecuteType, processor_id: ProcessorId, limit: int) -> list[EntryId]:
    sql = """
    SELECT entry_id FROM ln_failed_entries
    WHERE processor_id = %(processor_id)s
    ORDER BY created_at ASC
    LIMIT %(limit)s
    """

    rows = await execute(sql, {"processor_id": processor_id, "limit": limit})

    return [row["entry_id"] for row in rows]


async def remove_failed_entries(execute: ExecuteType, processor_id: ProcessorId, entry_ids: Iterable[EntryId]) -> None:
    sql = """
    DELETE FROM ln_failed_entries
    WHERE processor_id = %(processor_id)s
    AND entry_id = ANY(%(entry_ids)s)
    """

    await execute(sql, {"processor_id": processor_id, "entry_ids": list(entry_ids)})


async def count_failed_entries() -> dict[ProcessorId, int]:
    sql = """
    SELECT processor_id, COUNT(*) FROM ln_failed_entries GROUP BY processor_id
    """

    rows = await execute(sql)

    return {ProcessorId(row["processor_id"]): row["count"] for row in rows}
