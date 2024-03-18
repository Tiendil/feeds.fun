import uuid
from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.librarian import errors, operations
from ffun.librarian.entities import ProcessorPointer
from ffun.librarian.processors.base import Processor
from ffun.library import domain as l_domain
from ffun.library.entities import Entry, ProcessedState
from ffun.ontology import domain as o_domain


logger = logging.get_module_logger()


@run_in_transaction
async def push_entries_and_move_pointer(execute: ExecuteType, next_pointer: ProcessorPointer, entry_ids: Iterable[uuid.UUID]) -> None:
    await operations.push_entries_to_processor_queue(execute,
                                                     processor_id=next_pointer.processor_id,
                                                     entry_ids=entry_ids)

    await operations.save_pointer(execute, pointer=next_pointer)


# most likely, this code should be in a separate worker with a more complex logic
# but for now it is ok to place it here
# TODO: tests
async def plan_processor_queue(processor_id: int, limit: int) -> None:
    # TODO: maybe it will be a good idea to push more entries to the queue
    #       but rarelly, not every time
    pointer = await operations.get_or_create_pointer(processor_id=processor_id)

    next_entries = await l_domain.get_entries_after_pointer(created_at=pointer.pointer_created_at,
                                                            entry_id=pointer.pointer_entry_id,
                                                            limit=limit)

    if not next_entries:
        return

    last_entry = next_entries[-1]

    next_pointer = ProcessorPointer(processor_id=processor_id,
                                    pointer_created_at=last_entry[1],
                                    pointer_entry_id=last_entry[0])

    await push_entries_and_move_pointer(next_pointer, [entry[0] for entry in next_entries])


# TODO: save processing errors in the database
# TODO: tests
@logging.bound_function(skip=("processor",))
async def process_entry(processor_id: int, processor: Processor, entry: Entry) -> None:
    logger.info("dicover_tags", entry=entry, processor_id=processor_id)

    try:
        tags = await processor.process(entry)

        tags_for_log = [tag.raw_uid for tag in tags]
        tags_for_log.sort()

        logger.info("tags_found", tags=tags_for_log)

        await o_domain.apply_tags_to_entry(entry.id, processor_id, tags)
    except errors.SkipEntryProcessing as e:
        logger.warning("processor_requested_to_skip_entry", error_info=str(e))
        # do nothing in such case, see: https://github.com/Tiendil/feeds.fun/issues/176
    except Exception as e:
        await operations.add_entries_to_failed_storage(processor_id, [entry.id])
        raise errors.UnexpectedErrorInProcessor(processor_id=processor_id, entry_id=entry.id) from e
    else:
        logger.info("processor_successed")
        await l_domain.mark_entry_as_processed(
            processor_id=processor_id, entry_id=entry.id, state=ProcessedState.success, error=None
        )
    finally:
        await operations.remove_entries_from_processor_queue(processor_id, [entry.id])

    logger.info("entry_processed")
