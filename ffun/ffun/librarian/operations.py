import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

import psycopg
from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.librarian.entities import ProcessorPointer
from ffun.library.entities import Entry, ProcessedState
from ffun.library.settings import settings
from pypika import Field, PostgreSQLQuery, Table


logger = logging.get_module_logger()


def row_to_processor_pointer(row: dict[str, Any]) -> ProcessorPointer:
    return ProcessorPointer(
        processor_id=row["processor_id"],
        pointer_created_at=row["pointer_created_at"],
        pointer_entity_id=row["pointer_entity_id"],
    )


async def get_pointer(processor_id: int) -> ProcessorPointer:
    sql = """
    SELECT * FROM ln_processor_pointers
    WHERE processor_id = %(processor_id)s
    """

    row = await execute(sql, {"processor_id": processor_id})

    if row:
        return row_to_processor_pointer(row[0])

    return await create_pointer(processor_id)


async def create_pointer(processor_id: int) -> ProcessorPointer:
    sql = """
    INSERT INTO ln_processor_pointers (processor_id)
    VALUES (%(processor_id)s)
    RETURNING *
    """

    try:
        row = await execute(sql, {"processor_id": processor_id})
    except psycopg.UniqueViolation:
        return await get_pointer(processor_id)

    return row_to_processor_pointer(row[0])


async def save_pointer(pointer: ProcessorPointer) -> None:
    sql = """
    UPDATE ln_processor_pointers
    SET pointer_created_at = %(pointer_created_at)s,
        pointer_entity_id = %(pointer_entity_id)s
        updated_at = NOW()
    WHERE processor_id = %(processor_id)s
    RETURNING *
    """

    row = await execute(sql, {"processor_id": pointer.processor_id,
                              "pointer_created_at": pointer.pointer_created_at,
                              "pointer_entity_id": pointer.pointer_entity_id})

    if not row:
        raise NotImplementedError("Can't save unexisting pointer")


async def push_entries_to_processor_queue(processor_id: int, entry_ids: Iterable[uuid.UUID]) -> None:
    query = PostgreSQLQuery.into('ln_processor_queue').columns('processor_id', 'entry_id')

    for entry_id in entry_ids:
        query = query.insert(processor_id, entry_id)

    await execute(str(query))


async def get_entries_to_process(processor_id: int, n: int) -> set[uuid.UUID]:
    sql = """
    SELECT entry_id FROM ln_processor_queue
    WHERE processor_id = %(processor_id)s
    ORDER BY created_at
    LIMIT %(n)s
    """

    rows = await execute(sql, {"processor_id": processor_id, "n": n})

    return {row["entry_id"] for row in rows}


async def remove_entries_from_processor_queue(processor_id: int, entry_ids: Iterable[uuid.UUID]) -> None:
    sql = """
    DELETE FROM ln_processor_queue
    WHERE processor_id = %(processor_id)s
    AND entry_id = ANY(%(entry_ids)s)
    """

    await execute(sql, {"processor_id": processor_id, "entry_ids": list(entry_ids)})
