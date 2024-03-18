import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

import psycopg
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.librarian import errors
from ffun.librarian.entities import ProcessorPointer
from ffun.library.entities import Entry, ProcessedState
from ffun.library.settings import settings
from pypika import Field, PostgreSQLQuery, Table


logger = logging.get_module_logger()


def row_to_processor_pointer(row: dict[str, Any]) -> ProcessorPointer:
    return ProcessorPointer(
        processor_id=row["processor_id"],
        pointer_created_at=row["pointer_created_at"],
        pointer_entry_id=row["pointer_entry_id"],
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
    except psycopg.errors.UniqueViolation:
        return await get_pointer(processor_id)

    return row_to_processor_pointer(row[0])


async def delete_pointer(processor_id: int) -> None:
    sql = """
    DELETE FROM ln_processor_pointers
    WHERE processor_id = %(processor_id)s
    """

    await execute(sql, {"processor_id": processor_id})


async def save_pointer(execute: ExecuteType, pointer: ProcessorPointer) -> None:
    sql = """
    UPDATE ln_processor_pointers
    SET pointer_created_at = %(pointer_created_at)s,
        pointer_entry_id = %(pointer_entry_id)s,
        updated_at = NOW()
    WHERE processor_id = %(processor_id)s
    RETURNING *
    """

    row = await execute(sql, {"processor_id": pointer.processor_id,
                              "pointer_created_at": pointer.pointer_created_at,
                              "pointer_entry_id": pointer.pointer_entry_id})

    if not row:
        raise errors.CanNotSaveUnexistingPointer()


async def push_entries_to_processor_queue(execute: ExecuteType, processor_id: int, entry_ids: Iterable[uuid.UUID]) -> None:
    query = PostgreSQLQuery.into('ln_processors_queue').columns('processor_id', 'entry_id')

    for entry_id in entry_ids:
        query = query.insert(processor_id, entry_id)

    await execute(str(query))


async def get_entries_to_process(processor_id: int, n: int) -> list[uuid.UUID]:
    sql = """
    SELECT entry_id FROM ln_processors_queue
    WHERE processor_id = %(processor_id)s
    ORDER BY created_at ASC
    LIMIT %(n)s
    """

    rows = await execute(sql, {"processor_id": processor_id, "n": n})

    return [row["entry_id"] for row in rows]


async def remove_entries_from_processor_queue(processor_id: int, entry_ids: Iterable[uuid.UUID]) -> None:
    sql = """
    DELETE FROM ln_processors_queue
    WHERE processor_id = %(processor_id)s
    AND entry_id = ANY(%(entry_ids)s)
    """

    await execute(sql, {"processor_id": processor_id, "entry_ids": list(entry_ids)})


async def clear_processor_queue(processor_id: int) -> None:
    sql = """
    DELETE FROM ln_processors_queue
    WHERE processor_id = %(processor_id)s
    """

    await execute(sql, {"processor_id": processor_id})


async def add_entries_to_failed_storage(processor_id: int, entry_ids: Iterable[uuid.UUID]) -> None:
    query = PostgreSQLQuery.into('ln_failed_entries').columns('processor_id', 'entry_id')

    for entry_id in entry_ids:
        query = query.insert(processor_id, entry_id)

    await execute(str(query))


async def get_failed_entries(processor_id: int, n: int) -> list[uuid.UUID]:
    sql = """
    SELECT entry_id FROM ln_failed_entries
    WHERE processor_id = %(processor_id)s
    ORDER BY created_at ASC
    LIMIT %(n)s
    """

    rows = await execute(sql, {"processor_id": processor_id, "n": n})

    return [row["entry_id"] for row in rows]


async def remove_failed_entries(processor_id: int, entry_ids: Iterable[uuid.UUID]) -> None:
    sql = """
    DELETE FROM ln_failed_entries
    WHERE processor_id = %(processor_id)s
    AND entry_id = ANY(%(entry_ids)s)
    """

    await execute(sql, {"processor_id": processor_id, "entry_ids": list(entry_ids)})
