from collections.abc import Iterable, Sequence

from ffun.core import logging
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
)
from ffun.domain.entities import EntryId, ProcessorId
from ffun.feeds_collections.collections import collections
from ffun.library import domain as l_domain
from ffun.llms_framework.entities import LLMApiKeyType
from ffun.queues import domain as q_domain
from ffun.queues.entities import QueueKind, QueueRecord, QueueRecordId

logger = logging.get_module_logger()


async def push_entries_to_process(entry_ids: Iterable[EntryId], processor_id: ProcessorId | None = None) -> None:
    items = [EntryToProcess(entry_id=entry_id, processor_id=processor_id) for entry_id in entry_ids]

    await q_domain.push(QueueKind.entries_to_process, items)


async def get_entries_to_tag(processor_id: ProcessorId, limit: int) -> list[QueueRecord[EntryToTag]]:
    return await q_domain.pull(QueueKind.entries_to_tag, EntryToTag, secondary_id=processor_id, limit=limit)


async def push_entries_to_tag(
    processor_id: ProcessorId, entry_ids: Iterable[EntryId], llm_api_key_type: LLMApiKeyType | None
) -> None:
    items = [EntryToTag(entry_id=entry_id, llm_api_key_type=llm_api_key_type) for entry_id in entry_ids]

    await q_domain.push(QueueKind.entries_to_tag, items, secondary_id=processor_id)


async def acknowledge(record_ids: Sequence[QueueRecordId]) -> int:
    return await q_domain.acknowledge(record_ids)


async def _entries_in_collections(entries_ids: Iterable[EntryId]) -> dict[EntryId, bool]:
    feed_links = await l_domain.get_feed_links_for_entries(entries_ids)

    return {
        entry_id: any(collections.has_feed(link.feed_id) for link in links) for entry_id, links in feed_links.items()
    }


def _processor_dispatch_decision(
    processor: ProcessorDispatchInfo, item: EntryToProcess, *, in_collection: bool
) -> DispatchDecision | None:
    route = _processor_dispatch_route(processor, in_collection=in_collection)

    if route is None:
        logger.info(
            "proccessor_is_not_allowed_for_entry",
            processor_id=processor.processor_id,
            entry_id=item.entry_id,
            in_collection=in_collection,
        )
        return None

    logger.info(
        "proccessor_is_allowed_for_entry",
        processor_id=processor.processor_id,
        entry_id=item.entry_id,
        llm_api_key_type=route.llm_api_key_type,
    )

    return DispatchDecision(llm_api_key_type=route.llm_api_key_type)


def _processor_dispatch_route(
    processor: ProcessorDispatchInfo, *, in_collection: bool
) -> ProcessorDispatchRoute | None:
    for route in processor.routes:
        if in_collection and route.allowed_for_collections:
            return route

        if not in_collection and route.allowed_for_users:
            return route

    return None


def _processor_items_to_tag(
    processor: ProcessorDispatchInfo, items: Sequence[EntryToProcess], entries_in_collections: dict[EntryId, bool]
) -> list[EntryToTag]:
    processor_items = []

    for item in items:
        if item.processor_id is not None and item.processor_id != processor.processor_id:
            continue

        decision = _processor_dispatch_decision(
            processor, item, in_collection=entries_in_collections.get(item.entry_id, False)
        )

        if decision is None:
            continue

        processor_items.append(EntryToTag(entry_id=item.entry_id, llm_api_key_type=decision.llm_api_key_type))

    return processor_items


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
        processor_items = _processor_items_to_tag(processor, items, entries_in_collections)
        await q_domain.push(QueueKind.entries_to_tag, processor_items, secondary_id=processor.subqueue_id)

    record_ids = [record.id for record in records if record.id is not None]

    await acknowledge(record_ids)

    logger.info("entries_dispatched", entries_number=len(records), processors_number=len(processors))

    return len(records)
