
import datetime

from ffun.core import logging
from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain

from . import openai_client, tags
from .processors.base import Processor

logger = logging.get_module_logger()


# TODO: save processing errors in the database
@logging.bound_function(skip=('processor',))
async def process_entry(processor_id: int, processor: Processor, entry: Entry) -> None:
    logger.info('dicover_tags', entry=entry, processor_id=processor_id)

    try:
        found_tags = await processor.process(entry)

        normalized_tags = tags.normalize_tags(found_tags)

        logger.info('tags_found', tags=normalized_tags)

        await o_domain.apply_tags_to_entry(entry.id, normalized_tags)
    except Exception:
        logger.exception('unexpected_error_in_processor')
        raise
    finally:
        await l_domain.mark_entry_as_processed(processor_id=processor_id,
                                               entry_id=entry.id)

    logger.info('entry_processed')
