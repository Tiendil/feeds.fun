import datetime
import logging
import uuid
from typing import Any, Iterable

import psycopg
from ffun.core.postgresql import execute
from ffun.library.entities import Entry

logger = logging.getLogger(__name__)


async def get_last_entry_date(processor_id: int) -> datetime.datetime:
    sql = 'SELECT MAX(cataloged_at) AS border FROM ln_entry_process_info WHERE processor_id = %(processor_id)s'

    rows = await execute(sql, {'processor_id': processor_id})

    if not rows:
        return datetime.datetime.min

    border = rows[0]['border']

    if border is None:
        return datetime.datetime.min

    return border


async def mark_as_processed(
        entry_id: uuid.UUID, processor_id: int, cataloged_at: datetime.datetime, processed_at: datetime.datetime|None
) -> None:
    sql = '''
    INSERT INTO ln_entry_process_info (entry_id, processor_id, cataloged_at, processed_at)
    VALUES (%(entry_id)s, %(processor_id)s, %(cataloged_at)s, %(processed_at)s)
    ON CONFLICT (entry_id, processor_id) DO UPDATE SET processed_at = %(processed_at)s
    '''

    await execute(sql, {'processor_id': processor_id,
                        'entry_id': entry_id,
                        'processed_at': processed_at,
                        'cataloged_at': cataloged_at})
