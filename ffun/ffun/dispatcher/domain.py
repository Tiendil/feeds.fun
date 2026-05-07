from collections.abc import Iterable, Sequence

from ffun.core import logging
from ffun.dispatcher.entities import EntryToProcess
from ffun.domain.entities import EntryId
from ffun.queues import domain as q_domain
from ffun.queues.entities import QueueKind, QueueRecord, QueueRecordId

logger = logging.get_module_logger()


async def push_entries_to_process(entry_ids: Iterable[EntryId]) -> None:
    items = [EntryToProcess(entry_id=entry_id) for entry_id in entry_ids]

    await q_domain.push(QueueKind.entries_to_process, items)


async def get_entries_to_tag(processor_id: int, limit: int) -> list[QueueRecord[EntryToProcess]]:
    return await q_domain.pull(QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor_id, limit=limit)


async def push_entries_to_tag(processor_id: int, entry_ids: Iterable[EntryId]) -> None:
    items = [EntryToProcess(entry_id=entry_id) for entry_id in entry_ids]

    await q_domain.push(QueueKind.entries_to_tag, items, secondary_id=processor_id)


async def acknowledge(record_ids: Sequence[QueueRecordId]) -> int:
    return await q_domain.acknowledge(record_ids)


async def dispatch_entries(processor_ids: Sequence[int], limit: int) -> int:
    if not processor_ids:
        logger.info("no_processors_to_dispatch_entries")
        return 0

    records = await q_domain.pull(QueueKind.entries_to_process, EntryToProcess, limit=limit)

    if not records:
        logger.info("no_entries_to_dispatch")
        return 0

    items = [record.item for record in records]

    for processor_id in processor_ids:
        await q_domain.push(QueueKind.entries_to_tag, items, secondary_id=processor_id)

    record_ids = [record.id for record in records if record.id is not None]

    await acknowledge(record_ids)

    logger.info("entries_dispatched", entries_number=len(records), processors_number=len(processor_ids))

    return len(records)
