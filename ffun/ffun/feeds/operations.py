
import datetime
import logging
import uuid

import psycopg
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction

from .entities import Feed

logger = logging.getLogger(__name__)


def row_to_feed(row: dict) -> Feed:
    return Feed(id=row['id'],
                url=row['url'],
                load_attempted_at=row['load_attempted_at'],
                loaded_at=row['loaded_at'])


sql_insert_feed = '''
INSERT INTO f_feeds (id, url)
VALUES (%(id)s, %(url)s)
ON CONFLICT (id) DO NOTHING
'''


async def save_feeds(feeds: list[Feed]) -> None:

    for feed in feeds:
        try:
            await execute(sql_insert_feed,
                          {'id': feed.id,
                           'url': feed.url})
        except psycopg.errors.UniqueViolation as e:
            logger.warning('unique violation while saving feed %s', e)


@run_in_transaction
async def get_next_feeds_to_load(execute: ExecuteType,
                                 number: int,
                                 loaded_before: datetime.timedelta) -> list[Feed]:
    sql = '''
    SELECT *
    FROM f_feeds
    WHERE load_attempted_at <= %(loaded_before)s
    ORDER BY load_attempted_at ASC
    LIMIT %(number)s
    FOR UPDATE SKIP LOCKED
    '''

    rows = await execute(sql, {'number': number,
                               'loaded_before': loaded_before})

    ids = [row['id'] for row in rows]

    sql = '''
    UPDATE f_feeds
    SET load_attempted_at = NOW(),
        updated_at = NOW()
    WHERE id = ANY(%(ids)s)
    '''

    await execute(sql, {'ids': ids})

    return [row_to_feed(row) for row in rows]


async def mark_feed_as_loaded(feed_id: uuid.UUID) -> None:
    sql = '''
    UPDATE f_feeds
    SET loaded_at = NOW(),
        updated_at = NOW()
    WHERE id = %(id)s
    '''

    await execute(sql, {'id': feed_id})


async def get_all_feeds() -> list[Feed]:
    sql = '''
    SELECT *
    FROM f_feeds
    ORDER BY created_at ASC
    '''

    rows = await execute(sql)

    return [row_to_feed(row) for row in rows]
