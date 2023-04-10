import datetime
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
            logger.warning('racing is possible: unique violation while saving entry %s', e)


async def check_stored_entries_by_external_ids(external_ids: Iterable[str]) -> set[str]:
    sql = 'SELECT external_id FROM l_entries WHERE external_id = ANY(%(external_ids)s)'

    rows = await execute(sql, {'external_ids': external_ids})

    return {row['external_id'] for row in rows}


sql_select_entries = '''SELECT * FROM l_entries WHERE id = ANY(%(ids)s)'''


async def get_entries_by_ids(ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Entry|None]:
    rows = await execute(sql_select_entries, {'ids': ids})

    result: dict[uuid.UUID, Entry|None] = {id: None for id in ids}

    for row in rows:
        result[row['id']] = row_to_entry(row)

    return result


async def get_entries_by_filter(feeds_ids: Iterable[uuid.UUID],
                                period: datetime.timedelta|None,
                                limit: int) -> list[Entry]:

    if period is None:
        period = datetime.timedelta(days=100 * 365)

    sql = '''
    SELECT * FROM l_entries
    WHERE feed_id = ANY(%(feeds_ids)s) AND cataloged_at > NOW() - %(period)s
    ORDER BY cataloged_at DESC
    LIMIT %(limit)s'''

    rows = await execute(sql, {'feeds_ids': feeds_ids,
                               'period': period,
                               'limit': limit})

    return [row_to_entry(row) for row in rows]


async def get_new_entries(from_time: datetime.datetime, limit: int = 1000) -> list[Entry]:
    sql = '''
    SELECT * FROM l_entries
    WHERE cataloged_at > %(from_time)s
    ORDER BY cataloged_at ASC
    LIMIT %(limit)s
    '''

    rows = await execute(sql, {'from_time': from_time,
                               'limit': limit})

    return [row_to_entry(row) for row in rows]
