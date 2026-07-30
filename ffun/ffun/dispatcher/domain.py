import contextlib
import datetime
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence

from ffun.core import logging, utils
from ffun.core.concurrency import ConcurrentMapper
from ffun.dispatcher import entries_cache, errors, operations
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryAuthorization,
    EntryProcessingStatus,
    EntryProcessingStatusUpdate,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
)
from ffun.domain.datetime_intervals import (
    LIFETIME_INTERVAL_START_MARKER,
    day_interval_start,
    month_interval_start,
)
from ffun.domain.entities import ProcessorId, UserId
from ffun.entitlements.entities import EffectiveEntitlementInterval, EntitlementKindId
from ffun.markers import domain as m_domain
from ffun.markers.entities import Marker
from ffun.product.entities import Resource
from ffun.queues import domain as q_domain
from ffun.queues.entities import QueueItemToPush, QueueKind, QueueRecord, QueueRecordId
from ffun.resources import domain as r_domain
from ffun.resources import entities as r_entities

SAAS_TOKENS_PER_USER_ENTRY = 1

logger = logging.get_module_logger()

_TOKEN_ENTITLEMENT_KINDS = (
    EntitlementKindId.day_tokens,
    EntitlementKindId.month_tokens,
    EntitlementKindId.lifetime_tokens,
)

_ALLOWED_PROCESSING_STATUSES = {
    None,  # first-time processing for this processor
    EntryProcessingStatus.skipped_by_processor,  # reprocess because of a potential relinking of an entry
    EntryProcessingStatus.skipped_by_dispatcher,  # reprocess because of a potential relinking of an entry
    EntryProcessingStatus.retry_requested,  # explicit request to redispatch
}


get_entries_processing_statuses = operations.get_entries_processing_statuses
get_entries_by_processing_status = operations.get_entries_by_processing_status
count_entries_by_processing_status = operations.count_entries_by_processing_status
set_entry_processing_statuses = operations.set_entry_processing_statuses
remove_entry_processing_statuses = operations.remove_entry_processing_statuses
entries_in_collections = entries_cache.entries_in_collections


async def move_failed_entries_to_processor_queue(processor_id: ProcessorId, limit: int) -> None:
    failed_entries = await get_entries_by_processing_status(processor_id, EntryProcessingStatus.failed, limit)

    if not failed_entries:
        return

    await set_entry_processing_statuses(
        [
            EntryProcessingStatusUpdate(
                processor_id=processor_id,
                entry_id=entry_id,
                status=EntryProcessingStatus.retry_requested,
            )
            for entry_id in failed_entries
        ]
    )
    await q_domain.push(
        QueueKind.entries_to_process,
        [
            QueueItemToPush(item=EntryToProcess(entry_id=entry_id, processor_id=processor_id))
            for entry_id in failed_entries
        ],
    )


def _token_reservation_specification(
    user_id: UserId,
    entitlements: Mapping[EntitlementKindId, EffectiveEntitlementInterval | None],
) -> r_entities.ResourceReservationSpecification:
    return r_entities.ResourceReservationSpecification(
        user_id=user_id,
        limits=tuple(
            entitlement.value if entitlement is not None else None
            for entitlement in (entitlements.get(kind) for kind in _TOKEN_ENTITLEMENT_KINDS)
        ),
    )


def _token_reservation_options(
    authorization_time: datetime.datetime,
) -> tuple[r_entities.ResourceReservationOption, ...]:
    return (
        r_entities.ResourceReservationOption(
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(authorization_time),
        ),
        r_entities.ResourceReservationOption(
            kind=Resource.month_token_usage,
            interval_started_at=month_interval_start(authorization_time),
        ),
        r_entities.ResourceReservationOption(
            kind=Resource.lifetime_token_usage,
            interval_started_at=LIFETIME_INTERVAL_START_MARKER,
        ),
    )


async def _authorize_entry(item: EntryToProcess, cache: entries_cache.EntriesCache) -> EntryAuthorization:
    if cache.entry_in_collection(item.entry_id):
        return EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())

    user_ids = cache.entry_user_ids(item.entry_id)

    # TODO: temporary global authorization for entries linked to users with API keys.
    #       Remove together with the legacy API-key consumption logic.
    if cache.users_have_api_keys(user_ids):
        return EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())

    authorization_time = utils.now()
    specifications = [
        _token_reservation_specification(user_id, cache.user_entitlements(user_id))
        for user_id in sorted(user_ids, key=str)
    ]
    reservations = await r_domain.try_to_reserve_in_order(
        amount=SAAS_TOKENS_PER_USER_ENTRY,
        options=_token_reservation_options(authorization_time),
        specifications=specifications,
    )

    return EntryAuthorization(
        entry_id=item.entry_id,
        globally_visible=False,
        reservations=tuple(reservations),
    )


@contextlib.asynccontextmanager
async def _entry_authorization(
    item: EntryToProcess,
    cache: entries_cache.EntriesCache,
) -> AsyncIterator[EntryAuthorization]:
    authorization = await _authorize_entry(item, cache)

    try:
        yield authorization
    except BaseException:
        await r_domain.convert_reserved_to_used(list(authorization.reservations), used=0)
        raise
    else:
        await r_domain.convert_reserved_to_used(
            list(authorization.reservations),
            used=SAAS_TOKENS_PER_USER_ENTRY,
        )


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


async def _mark_entry_tags_visible(authorization: EntryAuthorization, settled_user_ids: Iterable[UserId]) -> None:
    if authorization.globally_visible:
        await m_domain.set_marker(user_ids=[None], marker=Marker.can_see_tags, entry_id=authorization.entry_id)
        return

    await m_domain.set_marker(
        user_ids=settled_user_ids,
        marker=Marker.can_see_tags,
        entry_id=authorization.entry_id,
    )


def _processors_for_item(
    item: EntryToProcess,
    processors: Sequence[ProcessorDispatchInfo],
    cache: entries_cache.EntriesCache,
) -> list[ProcessorDispatchInfo]:
    item_processors = []

    for processor in processors:
        targeted_to_processor = item.processor_id is None or item.processor_id == processor.processor_id

        if not targeted_to_processor:
            continue

        processing_status = cache.entry_processing_status(processor.processor_id, item.entry_id)

        if processing_status not in _ALLOWED_PROCESSING_STATUSES:
            continue

        item_processors.append(processor)

    return item_processors


async def _dispatch_entry_to_processors(
    processors: Sequence[ProcessorDispatchInfo],
    item: EntryToProcess,
    cache: entries_cache.EntriesCache,
) -> None:
    items_to_push = []
    status_updates = []
    in_collection = cache.entry_in_collection(item.entry_id)

    for processor in processors:
        decision = _processor_dispatch_decision(processor, item, in_collection=in_collection)

        if decision is None:
            status_updates.append(
                EntryProcessingStatusUpdate(
                    processor_id=processor.processor_id,
                    entry_id=item.entry_id,
                    status=EntryProcessingStatus.skipped_by_dispatcher,
                )
            )
            continue

        status_updates.append(
            EntryProcessingStatusUpdate(
                processor_id=processor.processor_id,
                entry_id=item.entry_id,
                status=EntryProcessingStatus.dispatched,
            )
        )
        items_to_push.append(
            QueueItemToPush(
                item=EntryToTag(entry_id=item.entry_id, route_id=decision.route_id),
                secondary_id=processor.subqueue_id,
            )
        )

    # Set status before pushing to queue, because in case of a persistent error on pushing it is better
    # to not push unprocessed entries, than infinitely push already processed entries causing money loses.
    await set_entry_processing_statuses(status_updates)

    await q_domain.push(QueueKind.entries_to_tag, items_to_push)


async def _process_entry(
    record: QueueRecord[EntryToProcess],
    processors: Sequence[ProcessorDispatchInfo],
    cache: entries_cache.EntriesCache,
) -> None:
    item = record.item
    item_processors = _processors_for_item(item, processors, cache)

    async with _entry_authorization(item, cache) as authorization:
        if not authorization.dispatch_allowed:
            await set_entry_processing_statuses(
                [
                    EntryProcessingStatusUpdate(
                        processor_id=processor.processor_id,
                        entry_id=item.entry_id,
                        status=EntryProcessingStatus.skipped_by_dispatcher,
                    )
                    for processor in item_processors
                ]
            )

            return

        await _dispatch_entry_to_processors(
            item_processors,
            item,
            cache,
        )

        settled_user_ids = {reservation.user_id for reservation in authorization.reservations}
        await _mark_entry_tags_visible(authorization, settled_user_ids)

        await operations.set_entry_dispatching_statuses(
            [item.entry_id],
            resources_consumed=bool(authorization.reservations),
        )


async def _process_retry_entry(
    record: QueueRecord[EntryToProcess],
    processors: Sequence[ProcessorDispatchInfo],
    cache: entries_cache.EntriesCache,
) -> None:
    item = record.item

    await _dispatch_entry_to_processors(
        _processors_for_item(item, processors, cache),
        item,
        cache,
    )


async def dispatch_entries(  # noqa: CCR001  # pylint: disable=too-many-locals
    processors: Sequence[ProcessorDispatchInfo],
    batch_size: int,
    concurrency: int,
) -> int:
    if not processors:
        logger.info("no_processors_to_dispatch_entries")
        return 0

    processor_ids = [processor.processor_id for processor in processors]

    if len(processor_ids) != len(set(processor_ids)):
        raise errors.DuplicatedProcessors()

    if concurrency <= 0:
        raise errors.InvalidConcurrency()

    records = await q_domain.pull(QueueKind.entries_to_process, EntryToProcess, limit=batch_size)

    if not records:
        logger.info("no_entries_to_dispatch")
        return 0

    dispatching_statuses = await operations.get_entries_dispatching_statuses(
        [record.item.entry_id for record in records]
    )
    retry_records = [record for record in records if record.item.entry_id in dispatching_statuses]
    first_time_records = [record for record in records if record.item.entry_id not in dispatching_statuses]

    cache = await entries_cache.create_entries_cache(
        items=[record.item for record in records],
        processors=processors,
        entitlement_kind_ids=_TOKEN_ENTITLEMENT_KINDS,
    )

    # Process entries separately to simplify error handling; batching would require
    # complex mapping between entries and users.
    async def process_record(record: QueueRecord[EntryToProcess]) -> bool:
        try:
            if record.item.entry_id in dispatching_statuses:
                await _process_retry_entry(record, processors, cache)
            else:
                await _process_entry(record, processors, cache)
        except Exception:
            logger.exception("entry_dispatch_failed", entry_id=record.item.entry_id)
            return False

        return True

    records_to_process = [*retry_records, *first_time_records]

    results = await ConcurrentMapper(
        items=records_to_process,
        handler=process_record,
        concurrency=concurrency,
    )()

    processed_record_ids: list[QueueRecordId] = []

    for record, processed in zip(records_to_process, results, strict=True):
        if not processed:
            continue

        assert record.id is not None
        processed_record_ids.append(record.id)

    if processed_record_ids:
        await q_domain.acknowledge(processed_record_ids)

    entries_processed = len(processed_record_ids)

    logger.info(
        "entries_dispatched",
        entries_number=entries_processed,
        failed_entries_number=len(records) - entries_processed,
        processors_number=len(processors),
    )

    return entries_processed
