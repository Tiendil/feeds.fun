import enum
from typing import NewType

from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId, ProcessorId
from ffun.queues.entities import BaseQueueItem

ProcessorRouteId = NewType("ProcessorRouteId", str)


class EntryProcessingStatus(enum.IntEnum):
    dispatched = 1
    processed = 2
    failed = 3
    skipped_by_processor = 4
    retry_requested = 5
    skipped_by_dispatcher = 6


class EntryToProcess(BaseQueueItem):
    entry_id: EntryId
    processor_id: ProcessorId | None = None


class EntryToTag(BaseQueueItem):
    entry_id: EntryId
    route_id: ProcessorRouteId


class DispatchDecision(BaseEntity):
    route_id: ProcessorRouteId


class ProcessorDispatchRoute(BaseEntity):
    id: ProcessorRouteId
    allowed_for_collections: bool
    allowed_for_users: bool


class ProcessorDispatchInfo(BaseEntity):
    processor_id: ProcessorId
    subqueue_id: ProcessorId
    routes: tuple[ProcessorDispatchRoute, ...]
