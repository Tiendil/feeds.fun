from typing import NewType

from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId, ProcessorId
from ffun.queues.entities import BaseQueueItem

ProcessorRouteId = NewType("ProcessorRouteId", str)


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
