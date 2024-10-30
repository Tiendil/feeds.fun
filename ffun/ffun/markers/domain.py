from ffun.core.postgresql import ExecuteType, run_in_transaction
from ffun.domain.entities import EntryId
from ffun.markers import operations

set_marker = operations.set_marker
remove_marker = operations.remove_marker
get_markers = operations.get_markers
remove_markers_for_entries = operations.remove_markers_for_entries


@run_in_transaction
async def tech_merge_markers(execute: ExecuteType, from_entry_id: EntryId, to_entry_id: EntryId) -> None:
    await operations.tech_merge_markers(execute, from_entry_id, to_entry_id)
