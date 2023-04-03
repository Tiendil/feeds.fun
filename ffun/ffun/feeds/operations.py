
import logging
import uuid

import psycopg
from ffun.core.postgresql import execute

from .entities import Feed

logger = logging.getLogger(__name__)


def row_to_feed(row: dict) -> Feed:
    return Feed(id=row['id'],
                url=row['url'],
                loaded_at=row['loaded_at'])


sql_insert_feed = '''
INSERT INTO f_feeds (id, url, loaded_at)
VALUES (%(id)s, %(url)s, %(loaded_at)s)
ON CONFLICT (id) DO NOTHING
'''


async def save_feeds(feeds: list[Feed]) -> None:

    for feed in feeds:
        try:
            await execute(sql_insert_feed,
                          {'id': feed.id,
                           'url': feed.url,
                           'loaded_at': feed.loaded_at})
        except psycopg.errors.UniqueViolation as e:
            logger.warning('unique violation while saving feed %s', e)


async def get_next_feeds_to_load(number: int) -> list[Feed]:
    sql = '''
    SELECT *
    FROM f_feeds
    ORDER BY loaded_at ASC
    LIMIT %(number)s
    '''

    rows = await execute(sql, {'number': number})

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
