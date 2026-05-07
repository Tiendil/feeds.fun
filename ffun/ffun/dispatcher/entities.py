from ffun.domain.entities import EntryId
from ffun.queues.entities import BaseQueueItem


class EntryToProcess(BaseQueueItem):
    entry_id: EntryId
