
import datetime
import uuid

import psycopg
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction

from .entities import Feed, FeedError, FeedState

logger = logging.get_module_logger()


def row_to_feed(row: dict) -> Feed:
    return Feed(id=row['id'],
                url=row['url'],
                state=FeedState(row['state']),
                last_error=FeedError(row['last_error']) if row['last_error'] else None,
                load_attempted_at=row['load_attempted_at'],
                loaded_at=row['loaded_at'],
                title=row['title'],
                description=row['description'])


sql_insert_feed = '''
INSERT INTO f_feeds (id, url, state, title, description)
VALUES (%(id)s, %(url)s, %(state)s, %(title)s, %(description)s)
ON CONFLICT (id) DO NOTHING
ON CONFLICT (url) DO NOTHING
'''


async def save_feeds(feeds: list[Feed]) -> None:

    for feed in feeds:
        try:
            await execute(sql_insert_feed,
                          {'id': feed.id,
                           'url': feed.url,
                           'state': feed.state,
                           'title': feed.title,
                           'description': feed.description})
        except psycopg.errors.UniqueViolation:
            logger.warning('unique_violation_while_saving_feed', feed_id=feed.id)


@run_in_transaction
async def get_next_feeds_to_load(execute: ExecuteType,
                                 number: int,
                                 loaded_before: datetime.datetime) -> list[Feed]:
    sql = '''
    SELECT *
    FROM f_feeds
    WHERE load_attempted_at IS NULL OR load_attempted_at <= %(loaded_before)s
    ORDER BY load_attempted_at ASC NULLS FIRST
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


async def update_feed_info(feed_id: uuid.UUID, title: str, description: str) -> None:
    sql = '''
    UPDATE f_feeds
    SET title = %(title)s,
        description = %(description)s,
        updated_at = NOW()
    WHERE id = %(id)s
    '''

    await execute(sql, {'id': feed_id,
                        'title': title,
                        'description': description})


async def mark_feed_as_loaded(feed_id: uuid.UUID) -> None:
    sql = '''
    UPDATE f_feeds
    SET state = %(state)s,
        last_error = NULL,
        loaded_at = NOW(),
        updated_at = NOW()
    WHERE id = %(id)s
    '''

    await execute(sql, {'id': feed_id,
                        'state': FeedState.loaded})


async def mark_feed_as_failed(feed_id: uuid.UUID, state: FeedState, error: FeedError) -> None:
    sql = '''
    UPDATE f_feeds
    SET state = %(state)s,
        last_error = %(error)s,
        updated_at = NOW()
    WHERE id = %(id)s
    '''

    await execute(sql, {'id': feed_id,
                        'state': state,
                        'error': error})


async def get_all_feeds() -> list[Feed]:
    sql = '''
    SELECT *
    FROM f_feeds
    ORDER BY created_at ASC
    '''

    rows = await execute(sql)

    return [row_to_feed(row) for row in rows]
