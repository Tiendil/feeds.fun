
import logging
import uuid
from typing import Any, Iterable

import psycopg
from ffun.core.postgresql import execute

from .entities import Entry

logger = logging.getLogger(__name__)


sql_insert_entry = '''
INSERT INTO l_entries (id, feed_id, title, body,
                       external_id, external_url, external_tags, published_at, cataloged_at)
VALUES (%(id)s, %(feed_id)s, %(title)s, %(body)s,
        %(external_id)s, %(external_url)s, %(external_tags)s, %(published_at)s, NOW())
'''


def row_to_entry(row: dict[str, Any]) -> Entry:
    return Entry(**row)


async def catalog_entries(entries: Iterable[Entry]) -> None:
    for entry in entries:
        try:
            await execute(sql_insert_entry,
                          {'id': entry.id,
                           'feed_id': entry.feed_id,
                           'title': entry.title,
                           'body': entry.body,
                           'external_id': entry.external_id,
                           'external_url': entry.external_url,
                           'external_tags': list(entry.external_tags),
                           'published_at': entry.published_at})
        except psycopg.errors.UniqueViolation as e:
            logger.warning('unique violation while saving entry %s', e)


sql_select_entries = '''SELECT * FROM l_entries WHERE id = ANY(%(ids)s)'''


async def get_entries(ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Entry|None]:
    rows = await execute(sql_select_entries, {'ids': ids})

    result: dict[uuid.UUID, Entry|None] = {id: None for id in ids}

    for row in rows:
        result[row['id']] = row_to_entry(row)

    return result
