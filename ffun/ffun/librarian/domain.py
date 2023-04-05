
import datetime
import logging

from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain

from . import openai_client, operations

_processors = [1]

logger = logging.getLogger(__name__)


async def discover_tags_for_entry(processor_id, entry: Entry) -> None:

    logging.info(f'dicover tags for entry {entry.id} for processor {processor_id}')

    if processor_id not in _processors:
        raise ValueError(f'Invalid processor id: {processor_id}')

    await operations.mark_as_processed(processor_id=processor_id,
                                       entry_id=entry.id,
                                       processed_at=None,
                                       cataloged_at=entry.cataloged_at)

    tags = await openai_client.get_labels_by_html(entry.body)

    logging.info('tags found: %s', tags)

    await o_domain.apply_tags_to_entry(entry.id, tags)

    await operations.mark_as_processed(processor_id=processor_id,
                                       entry_id=entry.id,
                                       processed_at=datetime.datetime.now(),
                                       cataloged_at=entry.cataloged_at)


async def process_new_entries(processor_id: int) -> None:

    logging.info(f'Processing new entries for processor {processor_id}')

    if processor_id not in _processors:
        raise ValueError(f'Invalid processor id: {processor_id}')

    while True:
        border = await operations.get_last_entry_date(processor_id)

        logging.info(f'Getting new entries for processor {processor_id} with border {border}')

        entries = await l_domain.get_new_entries(border)

        if not entries:
            logging.info('No new entries found')
            break

        logging.info('Found %s new entries', len(entries))

        for entry in entries:
            await discover_tags_for_entry(processor_id, entry)


# TODO: process_failed_entries
