from collections.abc import Iterable, Sequence

from ffun.core import logging
from ffun.dispatcher.entities import EntryToProcess, ProcessorDispatchInfo
from ffun.domain.entities import EntryId
from ffun.feeds_collections.collections import collections
from ffun.library import domain as l_domain
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


async def _entries_in_collections(entries_ids: Iterable[EntryId]) -> dict[EntryId, bool]:
    feed_links = await l_domain.get_feed_links_for_entries(entries_ids)

    return {
        entry_id: any(collections.has_feed(link.feed_id) for link in links) for entry_id, links in feed_links.items()
    }


def _processor_is_allowed(processor: ProcessorDispatchInfo, item: EntryToProcess, *, in_collection: bool) -> bool:
    if in_collection and not processor.allowed_for_collections:
        logger.info(
            "proccessor_not_allowed_for_collections", processor_id=processor.processor_id, entry_id=item.entry_id
        )
        return False

    if not in_collection and not processor.allowed_for_users:
        logger.info("proccessor_not_allowed_for_users", processor_id=processor.processor_id, entry_id=item.entry_id)
        return False

    logger.info("proccessor_is_allowed_for_entry", processor_id=processor.processor_id, entry_id=item.entry_id)

    return True


async def dispatch_entries(processors: Sequence[ProcessorDispatchInfo], limit: int) -> int:
    if not processors:
        logger.info("no_processors_to_dispatch_entries")
        return 0

    records = await q_domain.pull(QueueKind.entries_to_process, EntryToProcess, limit=limit)

    if not records:
        logger.info("no_entries_to_dispatch")
        return 0

    items = [record.item for record in records]
    entries_in_collections = await _entries_in_collections(item.entry_id for item in items)

    for processor in processors:
        processor_items = [
            item
            for item in items
            if _processor_is_allowed(processor, item, in_collection=entries_in_collections.get(item.entry_id, False))
        ]

        await q_domain.push(QueueKind.entries_to_tag, processor_items, secondary_id=processor.subqueue_id)

    record_ids = [record.id for record in records if record.id is not None]

    await acknowledge(record_ids)

    logger.info("entries_dispatched", entries_number=len(records), processors_number=len(processors))

    return len(records)
