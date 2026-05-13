from ffun.dispatcher import domain as d_domain
from ffun.dispatcher.entities import EntryProcessingStatus
from ffun.domain.entities import EntryId, ProcessorId


async def assert_processing_status(
    processor_id: ProcessorId, entry_id: EntryId, status: EntryProcessingStatus
) -> None:
    statuses = await d_domain.get_entries_processing_statuses([processor_id], [entry_id])

    assert statuses.get(processor_id, {}) == {entry_id: status}
