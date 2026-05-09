from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId, ProcessorId
from ffun.llms_framework.entities import LLMApiKeyType
from ffun.queues.entities import BaseQueueItem


class EntryToProcess(BaseQueueItem):
    entry_id: EntryId
    processor_id: ProcessorId | None = None


class EntryToTag(BaseQueueItem):
    entry_id: EntryId
    llm_api_key_type: LLMApiKeyType | None = None


class DispatchDecision(BaseEntity):
    llm_api_key_type: LLMApiKeyType | None = None


class ProcessorDispatchRoute(BaseEntity):
    allowed_for_collections: bool
    allowed_for_users: bool
    llm_api_key_type: LLMApiKeyType | None = None


class ProcessorDispatchInfo(BaseEntity):
    processor_id: ProcessorId
    subqueue_id: ProcessorId
    routes: tuple[ProcessorDispatchRoute, ...]
