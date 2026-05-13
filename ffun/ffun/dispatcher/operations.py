from collections.abc import Iterable

from ffun.core.postgresql import execute
from ffun.dispatcher.entities import EntryProcessingStatus
from ffun.domain.entities import EntryId, ProcessorId


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


async def set_entry_processing_statuses(
    processor_id: ProcessorId, entry_ids: Iterable[EntryId], status: EntryProcessingStatus
) -> None:
    ids = list(dict.fromkeys(entry_ids))

    if not ids:
        return

    sql = """
    WITH entry_ids AS (
        SELECT unnest(%(entry_ids)s::uuid[]) AS entry_id
    )
    INSERT INTO d_entry_processing_status (entry_id, processor_id, status)
    SELECT entry_id, %(processor_id)s, %(status)s
    FROM entry_ids
    ON CONFLICT (entry_id, processor_id) DO UPDATE SET
        status = EXCLUDED.status,
        updated_at = CURRENT_TIMESTAMP
    """

    await execute(sql, {"processor_id": processor_id, "entry_ids": ids, "status": int(status)})


async def remove_entry_processing_statuses(entry_ids: Iterable[EntryId]) -> None:
    ids = list(dict.fromkeys(entry_ids))

    if not ids:
        return

    sql = """
    DELETE FROM d_entry_processing_status
    WHERE entry_id = ANY(%(entry_ids)s)
    """

    await execute(sql, {"entry_ids": ids})
