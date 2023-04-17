
import logging
import uuid
from typing import Iterable

import psycopg
from bidict import bidict
from ffun.core.postgresql import execute

from .entities import Rule

logger = logging.getLogger(__name__)


def normalize_tags(tags: Iterable[int]) -> tuple[int, ...]:
    return tuple(sorted(tags))


def row_to_rule(row: dict) -> Rule:
    return Rule(id=row['id'],
                user_id=row['user_id'],
                tags=set(row['tags']),
                score=row['score'],
                created_at=row['created_at'])


async def create_rule(user_id: uuid.UUID, tags: Iterable[int], score: int) -> None:

    tags = normalize_tags(tags)
    key = ','.join(map(str, tags))

    sql = '''
        INSERT INTO s_rules (user_id, tags, key, score)
        VALUES (%(user_id)s, %(tags)s, %(key)s, %(score)s)
        '''

    try:
        await execute(sql, {'user_id': user_id, 'tags': tags, 'key': key, 'score': score})
    except psycopg.errors.UniqueViolation:
        logger.warning('Rule already exists: %s', key)


async def delete_rule(user_id: uuid.UUID, tags: Iterable[int]) -> None:

    tags = normalize_tags(tags)
    key = ','.join(map(str, tags))

    sql = '''
        DELETE FROM s_rules
        WHERE user_id = %(user_id)s AND key = %(key)s
        '''

    await execute(sql, {'user_id': user_id, 'key': key})


async def get_rules(user_id: uuid.UUID) -> list[Rule]:

    sql = '''
    SELECT id*
    FROM s_rules
    WHERE user_id = %(user_id)s
    '''

    rows = await execute(sql, {'user_id': user_id})

    return [row_to_rule(row) for row in rows]
