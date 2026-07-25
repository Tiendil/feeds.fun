import asyncio
import contextlib
import datetime
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence

from ffun.core import logging, utils
from ffun.dispatcher import entries_cache, errors, operations
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryAuthorization,
    EntryProcessingStatus,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
    ProcessorRouteId,
)
from ffun.domain.datetime_intervals import (
    LIFETIME_INTERVAL_START_MARKER,
    day_interval_start,
    month_interval_start,
)
from ffun.domain.entities import EntryId, ProcessorId, UserId
from ffun.entitlements import domain as e_domain
from ffun.entitlements.entities import EffectiveEntitlementInterval, EntitlementKindId
from ffun.markers import domain as m_domain
from ffun.markers.entities import Marker
from ffun.product.entities import Resource
from ffun.queues import domain as q_domain
from ffun.queues.entities import QueueKind, QueueRecord, QueueRecordId
from ffun.resources import domain as r_domain
from ffun.resources import entities as r_entities

SAAS_TOKENS_PER_USER_ENTRY = 1

logger = logging.get_module_logger()

_TOKEN_ENTITLEMENT_KINDS = (
    EntitlementKindId.day_tokens,
    EntitlementKindId.month_tokens,
    EntitlementKindId.lifetime_tokens,
)


get_entries_processing_statuses = operations.get_entries_processing_statuses
get_entries_by_processing_status = operations.get_entries_by_processing_status
count_entries_by_processing_status = operations.count_entries_by_processing_status
set_entry_processing_statuses = operations.set_entry_processing_statuses
remove_entry_processing_statuses = operations.remove_entry_processing_statuses
_entries_in_collections = entries_cache.entries_in_collections


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


def _token_reservation_specification(
    user_id: UserId,
    entitlements: Mapping[EntitlementKindId, EffectiveEntitlementInterval | None],
    authorization_time: datetime.datetime,
) -> r_entities.ResourceReservationSpecification:
    options: list[r_entities.ResourceReservationOption] = []

    option_definitions = (
        (EntitlementKindId.day_tokens, Resource.day_token_usage, day_interval_start(authorization_time)),
        (EntitlementKindId.month_tokens, Resource.month_token_usage, month_interval_start(authorization_time)),
        (
            EntitlementKindId.lifetime_tokens,
            Resource.lifetime_token_usage,
            LIFETIME_INTERVAL_START_MARKER,
        ),
    )

    for entitlement_kind, resource_kind, interval_started_at in option_definitions:
        entitlement = entitlements.get(entitlement_kind)

        if entitlement is None:
            continue

        options.append(
            r_entities.ResourceReservationOption(
                kind=resource_kind,
                interval_started_at=interval_started_at,
                limit=entitlement.value,
            )
        )

    return r_entities.ResourceReservationSpecification(
        user_id=user_id,
        amount=SAAS_TOKENS_PER_USER_ENTRY,
        options=tuple(options),
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
    entitlements = await e_domain.get_entitlements(
        sorted(user_ids, key=str),
        list(_TOKEN_ENTITLEMENT_KINDS),
    )
    specifications = [
        _token_reservation_specification(user_id, entitlements[user_id], authorization_time)
        for user_id in sorted(user_ids, key=str)
    ]
    reservations = await r_domain.try_to_reserve_in_order(specifications)

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
        await r_domain.convert_reservations_to_used(authorization.reservations, consume=False)
        raise
    else:
        await r_domain.convert_reservations_to_used(authorization.reservations, consume=True)


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
        await m_domain.set_marker(user_id=None, marker=Marker.can_see_tags, entry_id=authorization.entry_id)
        return

    for user_id in sorted(settled_user_ids, key=str):
        await m_domain.set_marker(user_id=user_id, marker=Marker.can_see_tags, entry_id=authorization.entry_id)


def _processor_items_to_tag(
    processor: ProcessorDispatchInfo,
    items: Sequence[EntryToProcess],
    cache: entries_cache.EntriesCache,
) -> tuple[list[EntryToTag], list[EntryId]]:
    processor_items = []
    skipped_entry_ids = []

    for item in items:
        decision = _processor_dispatch_decision(
            processor,
            item,
            in_collection=cache.entry_in_collection(item.entry_id),
        )

        if decision is None:
            skipped_entry_ids.append(item.entry_id)
            continue

        processor_items.append(EntryToTag(entry_id=item.entry_id, route_id=decision.route_id))

    return processor_items, skipped_entry_ids


def _processor_items_targeted_to_processor(
    processor: ProcessorDispatchInfo,
    items: Sequence[EntryToProcess],
) -> list[EntryToProcess]:
    return [item for item in items if item.processor_id is None or item.processor_id == processor.processor_id]


def _processor_items_allowed_by_status(
    processor: ProcessorDispatchInfo,
    processor_items: Sequence[EntryToProcess],
    cache: entries_cache.EntriesCache,
) -> list[EntryToProcess]:
    allowed_statuses = {
        None,  # first-time processing for this processor
        EntryProcessingStatus.skipped_by_processor,  # reprocess because of a potential relinking of an entry
        EntryProcessingStatus.skipped_by_dispatcher,  # reprocess because of a potential relinking of an entry
        EntryProcessingStatus.retry_requested,  # explicit request to redispatch
    }

    return [
        item
        for item in processor_items
        if cache.entry_processing_status(processor.processor_id, item.entry_id) in allowed_statuses
    ]


async def _dispatch_entries_to_processor(
    processor: ProcessorDispatchInfo,
    items: Sequence[EntryToProcess],
    cache: entries_cache.EntriesCache,
    *,
    dispatch_allowed: bool = True,
) -> None:
    processor_items = _processor_items_allowed_by_status(processor, items, cache)
    processor_items = _processor_items_targeted_to_processor(processor, processor_items)

    if dispatch_allowed:
        processor_items_to_tag, skipped_entry_ids = _processor_items_to_tag(processor, processor_items, cache)
    else:
        processor_items_to_tag = []
        skipped_entry_ids = [item.entry_id for item in processor_items]

    await set_entry_processing_statuses(
        processor.processor_id,
        skipped_entry_ids,
        EntryProcessingStatus.skipped_by_dispatcher,
    )

    # Set status before pushing to queue, because in case of a persistent error on pushing it is better
    # to not push unprocessed entries, than infinitely push already processed entries causing money loses.
    await set_entry_processing_statuses(
        processor.processor_id,
        [item.entry_id for item in processor_items_to_tag],
        EntryProcessingStatus.dispatched,
    )

    await q_domain.push(QueueKind.entries_to_tag, processor_items_to_tag, secondary_id=processor.subqueue_id)


async def _process_entry(
    record: QueueRecord[EntryToProcess],
    processors: Sequence[ProcessorDispatchInfo],
    cache: entries_cache.EntriesCache,
) -> bool:
    item = record.item

    try:
        async with _entry_authorization(item, cache) as authorization:
            dispatch_allowed = authorization.globally_visible or bool(authorization.reservations)

            for processor in processors:
                await _dispatch_entries_to_processor(
                    processor,
                    [item],
                    cache,
                    dispatch_allowed=dispatch_allowed,
                )

            if dispatch_allowed:
                settled_user_ids = {reservation.user_id for reservation in authorization.reservations}
                await _mark_entry_tags_visible(authorization, settled_user_ids)

        assert record.id is not None
        await acknowledge([record.id])
    except Exception:
        logger.exception("entry_dispatch_failed", entry_id=item.entry_id)
        return False

    return True


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

    cache = await entries_cache.create_entries_cache(
        items=[record.item for record in records],
        processors=processors,
    )
    results = await asyncio.gather(
        *(_process_entry(record, processors, cache) for record in records),
        return_exceptions=True,
    )
    entries_processed = results.count(True)

    logger.info(
        "entries_dispatched",
        entries_number=entries_processed,
        failed_entries_number=len(records) - entries_processed,
        processors_number=len(processors),
    )

    return entries_processed
