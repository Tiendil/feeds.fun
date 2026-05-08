from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId
from ffun.queues.entities import BaseQueueItem


class EntryToProcess(BaseQueueItem):
    entry_id: EntryId


class ProcessorDispatchInfo(BaseEntity):
    processor_id: int
    subqueue_id: int
    allowed_for_collections: bool
    allowed_for_users: bool
