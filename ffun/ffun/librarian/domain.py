
import datetime
import logging

from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain

from . import openai_client
from .processors.base import Processor

logger = logging.getLogger(__name__)


# TODO: save processing errors in the database
async def process_entry(processor_id: int, processor: Processor, entry: Entry) -> None:
    logging.info(f'dicover tags for entry {entry.id} for processor {processor_id}')

    tags = await processor.process(entry)

    logging.info('tags found: %s', tags)

    await o_domain.apply_tags_to_entry(entry.id, tags)

    await l_domain.mark_entry_as_processed(processor_id=processor_id,
                                           entry_id=entry.id)

    logging.info('entry %s processed with processor %s', entry.id, processor_id)
