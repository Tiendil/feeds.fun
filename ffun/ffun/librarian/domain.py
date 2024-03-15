import uuid
from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.librarian import errors, operations
from ffun.librarian.processors.base import Processor
from ffun.library import domain as l_domain
from ffun.library.entities import Entry, ProcessedState
from ffun.ontology import domain as o_domain


logger = logging.get_module_logger()


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
    except errors.SkipAndContinueLater as e:
        logger.warning("processor_requested_to_skip_entry", error_info=str(e))
        await l_domain.mark_entry_as_processed(
            processor_id=processor_id, entry_id=entry.id, state=ProcessedState.retry_later, error=None
        )
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
