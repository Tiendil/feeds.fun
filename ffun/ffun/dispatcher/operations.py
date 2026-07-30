from collections.abc import Iterable

from ffun.core.postgresql import execute
from ffun.dispatcher.entities import EntryProcessingStatus
from ffun.domain.entities import EntryId, ProcessorId


async def get_entries_dispatching_statuses(entry_ids: Iterable[EntryId]) -> dict[EntryId, bool]:
    ids = list(set(entry_ids))

    if not ids:
        return {}

    sql = """
    SELECT entry_id, resources_consumed
    FROM d_entry_dispatching_status
    WHERE entry_id = ANY(%(entry_ids)s)
    """

    rows = await execute(sql, {"entry_ids": ids})

    return {row["entry_id"]: row["resources_consumed"] for row in rows}


async def set_entry_dispatching_statuses(entry_ids: Iterable[EntryId], resources_consumed: bool) -> None:
    ids = list(set(entry_ids))

    if not ids:
        return

    sql = """
    WITH entry_ids AS (
        SELECT unnest(%(entry_ids)s::uuid[]) AS entry_id
    )
    INSERT INTO d_entry_dispatching_status (entry_id, resources_consumed)
    SELECT entry_id, %(resources_consumed)s
    FROM entry_ids
    ON CONFLICT (entry_id) DO UPDATE SET
        resources_consumed = EXCLUDED.resources_consumed,
        updated_at = CURRENT_TIMESTAMP
    """

    await execute(sql, {"entry_ids": ids, "resources_consumed": resources_consumed})


async def get_entries_processing_statuses(
    processor_ids: Iterable[ProcessorId], entry_ids: Iterable[EntryId]
) -> dict[ProcessorId, dict[EntryId, EntryProcessingStatus]]:
    processor_ids_list = list(dict.fromkeys(processor_ids))
    ids = list(dict.fromkeys(entry_ids))
    statuses: dict[ProcessorId, dict[EntryId, EntryProcessingStatus]] = {
        processor_id: {} for processor_id in processor_ids_list
    }

    if not processor_ids_list or not ids:
        return statuses

    sql = """
    SELECT processor_id, entry_id, status
    FROM d_entry_processing_status
    WHERE processor_id = ANY(%(processor_ids)s)
      AND entry_id = ANY(%(entry_ids)s)
    """

    rows = await execute(sql, {"processor_ids": processor_ids_list, "entry_ids": ids})

    for row in rows:
        processor_id = ProcessorId(row["processor_id"])
        statuses[processor_id][row["entry_id"]] = EntryProcessingStatus(row["status"])

    return statuses


async def get_entries_by_processing_status(
    processor_id: ProcessorId, status: EntryProcessingStatus, limit: int
) -> list[EntryId]:
    sql = """
    SELECT entry_id
    FROM d_entry_processing_status
    WHERE processor_id = %(processor_id)s
      AND status = %(status)s
    ORDER BY updated_at ASC, entry_id ASC
    LIMIT %(limit)s
    """

    rows = await execute(
        sql,
        {"processor_id": processor_id, "status": int(status), "limit": limit},
    )

    return [row["entry_id"] for row in rows]


async def count_entries_by_processing_status(status: EntryProcessingStatus) -> dict[ProcessorId, int]:
    sql = """
    SELECT processor_id, COUNT(*) AS count
    FROM d_entry_processing_status
    WHERE status = %(status)s
    GROUP BY processor_id
    """

    rows = await execute(sql, {"status": int(status)})

    return {ProcessorId(row["processor_id"]): row["count"] for row in rows}


async def set_entry_processing_statuses(
    processor_ids: list[ProcessorId], entry_ids: Iterable[EntryId], status: EntryProcessingStatus
) -> None:
    unique_processor_ids = list(set(processor_ids))
    ids = list(dict.fromkeys(entry_ids))

    if not unique_processor_ids or not ids:
        return

    sql = """
    WITH entry_ids AS (
        SELECT unnest(%(entry_ids)s::uuid[]) AS entry_id
    ),
    processor_ids AS (
        SELECT unnest(%(processor_ids)s::smallint[]) AS processor_id
    )
    INSERT INTO d_entry_processing_status (entry_id, processor_id, status)
    SELECT entry_id, processor_id, %(status)s
    FROM entry_ids
    CROSS JOIN processor_ids
    ON CONFLICT (entry_id, processor_id) DO UPDATE SET
        status = EXCLUDED.status,
        updated_at = CURRENT_TIMESTAMP
    """

    await execute(
        sql,
        {
            "processor_ids": unique_processor_ids,
            "entry_ids": ids,
            "status": int(status),
        },
    )


async def remove_entry_processing_statuses(entry_ids: Iterable[EntryId]) -> None:
    ids = list(dict.fromkeys(entry_ids))

    if not ids:
        return

    sql = """
    DELETE FROM d_entry_processing_status
    WHERE entry_id = ANY(%(entry_ids)s)
    """

    await execute(sql, {"entry_ids": ids})


async def tech_truncate_entry_processing_statuses() -> None:
    await execute("TRUNCATE TABLE d_entry_processing_status")
