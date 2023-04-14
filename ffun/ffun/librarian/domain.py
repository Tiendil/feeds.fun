
import datetime
import logging

from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain

from . import openai_client, tags
from .processors.base import Processor

logger = logging.getLogger(__name__)


# TODO: save processing errors in the database
async def process_entry(processor_id: int, processor: Processor, entry: Entry) -> None:
    logger.info(f'dicover tags for entry {entry.id} for processor {processor_id}')

    found_tags = await processor.process(entry)

    normalized_tags = tags.normalize_tags(found_tags)

    logger.info('tags found: %s', normalized_tags)

    await o_domain.apply_tags_to_entry(entry.id, normalized_tags)

    await l_domain.mark_entry_as_processed(processor_id=processor_id,
                                           entry_id=entry.id)

    logger.info('entry %s processed with processor %s', entry.id, processor_id)
