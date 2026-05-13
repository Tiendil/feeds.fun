from collections.abc import Iterable, Sequence

from ffun.core import logging
from ffun.dispatcher import errors, operations
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryProcessingStatus,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
    ProcessorRouteId,
)
from ffun.domain.entities import EntryId, ProcessorId
from ffun.feeds_collections.collections import collections
from ffun.library import domain as l_domain
from ffun.markers import domain as m_domain
from ffun.markers.entities import Marker
from ffun.queues import domain as q_domain
from ffun.queues.entities import QueueKind, QueueRecord, QueueRecordId

logger = logging.get_module_logger()


get_entries_processing_statuses = operations.get_entries_processing_statuses
get_entries_by_processing_status = operations.get_entries_by_processing_status
count_entries_by_processing_status = operations.count_entries_by_processing_status
set_entry_processing_statuses = operations.set_entry_processing_statuses
remove_entry_processing_statuses = operations.remove_entry_processing_statuses


async def push_entries_to_process(entry_ids: Iterable[EntryId], processor_id: ProcessorId | None = None) -> None:
    items = [EntryToProcess(entry_id=entry_id, processor_id=processor_id) for entry_id in entry_ids]

    await q_domain.push(QueueKind.entries_to_process, items)


async def move_failed_entries_to_processor_queue(processor_id: ProcessorId, limit: int) -> None:
    failed_entries = await get_entries_by_processing_status(processor_id, EntryProcessingStatus.failed, limit)

    if not failed_entries:
        return

    await set_entry_processing_statuses(processor_id, failed_entries, EntryProcessingStatus.retry_requested)
    await push_entries_to_process(failed_entries, processor_id=processor_id)


async def get_entries_to_tag(processor_id: ProcessorId, limit: int) -> list[QueueRecord[EntryToTag]]:
    return await q_domain.pull(QueueKind.entries_to_tag, EntryToTag, secondary_id=processor_id, limit=limit)


async def push_entries_to_tag(
    processor_id: ProcessorId, entry_ids: Iterable[EntryId], route_id: ProcessorRouteId
) -> None:
    items = [EntryToTag(entry_id=entry_id, route_id=route_id) for entry_id in entry_ids]

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
        route_id=route.id,
    )

    return DispatchDecision(route_id=route.id)


def _processor_dispatch_route(
    processor: ProcessorDispatchInfo, *, in_collection: bool
) -> ProcessorDispatchRoute | None:
    for route in processor.routes:
        if in_collection and route.allowed_for_collections:
            return route

        if not in_collection and route.allowed_for_users:
            return route

    return None


async def _mark_entry_tags_visible(item: EntryToProcess, *, in_collection: bool) -> None:
    if in_collection:
        await m_domain.set_marker(user_id=None, marker=Marker.can_see_tags, entry_id=item.entry_id)
        return

    # TODO: temporary global visibility for all entries.
    #       Must be removed after removing processing entries with custom user API keys.
    await m_domain.set_marker(user_id=None, marker=Marker.can_see_tags, entry_id=item.entry_id)


async def _mark_entries_tags_visible(
    items: Sequence[EntryToProcess], entries_in_collections: dict[EntryId, bool]
) -> None:
    for item in items:
        await _mark_entry_tags_visible(item, in_collection=entries_in_collections.get(item.entry_id, False))


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

        processor_items.append(EntryToTag(entry_id=item.entry_id, route_id=decision.route_id))

    return processor_items


def _processor_items_allowed_by_status(
    processor_items: Sequence[EntryToTag],
    statuses: dict[EntryId, EntryProcessingStatus],
) -> list[EntryToTag]:
    allowed_statuses = {
        None,  # first-time processing for this processor
        EntryProcessingStatus.skipped,  # reprocess because of a potential relinking of an entry
        EntryProcessingStatus.retry_requested,  # explicit request to redispatch
    }

    return [item for item in processor_items if statuses.get(item.entry_id) in allowed_statuses]


async def dispatch_entries(processors: Sequence[ProcessorDispatchInfo], limit: int) -> int:
    if not processors:
        logger.info("no_processors_to_dispatch_entries")
        return 0

    processor_ids = [processor.processor_id for processor in processors]

    if len(processor_ids) != len(set(processor_ids)):
        raise errors.DuplicatedProcessors()

    records = await q_domain.pull(QueueKind.entries_to_process, EntryToProcess, limit=limit)

    if not records:
        logger.info("no_entries_to_dispatch")
        return 0

    items = [record.item for record in records]
    entries_in_collections = await _entries_in_collections(item.entry_id for item in items)

    await _mark_entries_tags_visible(items, entries_in_collections)
    statuses = await get_entries_processing_statuses(
        [processor.processor_id for processor in processors], [item.entry_id for item in items]
    )

    for processor in processors:
        processor_items = _processor_items_to_tag(processor, items, entries_in_collections)
        processor_items = _processor_items_allowed_by_status(processor_items, statuses.get(processor.processor_id, {}))
        # Set status before pushing to queue, because in case of a persistent error on pushing it is better
        # to not push unprocessed entries, than infinitely push already processed entries causing money loses.
        await set_entry_processing_statuses(
            processor.processor_id,
            [item.entry_id for item in processor_items],
            EntryProcessingStatus.dispatched,
        )

        await q_domain.push(QueueKind.entries_to_tag, processor_items, secondary_id=processor.subqueue_id)

    record_ids = [record.id for record in records if record.id is not None]

    await acknowledge(record_ids)

    logger.info("entries_dispatched", entries_number=len(records), processors_number=len(processors))

    return len(records)
