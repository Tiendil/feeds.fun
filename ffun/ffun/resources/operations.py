import datetime
import uuid
from typing import Any, Iterable

import psycopg
from ffun.core import logging
from ffun.core.postgresql import execute

from .entities import Resource

logger = logging.get_module_logger()


def row_to_entry(row: dict[str, Any]) -> Resource
    return Resource(user_id=row['user_id'],
                    kind=row['kind'],
                    interval_started_at=row['interval_started_at'],
                    used=row['used'],
                    reserved=row['reserved'])


async def initialize_resource(user_id: uuid.UUID,
                              kind: int,
                              interval_started_at: datetime.datetime) -> Resource:
    sql = """
        INSERT INTO r_resources (user_id, kind, interval_started_at)
        VALUES (%(user_id)s, %(kind)s, %(interval_started_at)s)
        ON CONFLICT (user_id, kind, interval_started_at) DO NOTHING
    """

    await execute(sql, {'user_id': user_id,
                        'kind': kind,
                        'interval_started_at': interval_started_at})

    sql = """
    SELECT * FROM r_resources
    WHERE user_id = %(user_id)s AND kind = %(kind)s AND interval_started_at = %(interval_started_at)s
    """

    results = await execute(sql, {'user_id': user_id,
                                  'kind': kind,
                                  'interval_started_at': interval_started_at})

    return row_to_entry(results[0])


async def load_resources(user_ids: Iterable[uuid.UUID],
                         kind: int,
                         interval_started_at: datetime.datetime) -> Any:
    sql = """
        SELECT * FROM r_resources
        WHERE user_id = ANY(%(user_ids)s) AND kind = %(kind)s AND interval_started_at = %(interval_started_at)s
    """

    results = await execute(sql, {'user_ids': list(user_ids),
                                  'kind': kind,
                                  'interval_started_at': interval_started_at})

    resources = {}

    for row in results:
        resources[row['user_id']] = row_to_entry(row)

    for user_id in user_ids:
        if user_id not in resources:
            resources[user_id] = await initialize_resource(user_id, kind, interval_started_at)

    return resources


async def try_to_reserve(user_id: uuid.UUID,
                         kind: int,
                         interval_started_at: datetime.datetime,
                         amount: int,
                         limit: int) -> bool:
    sql = """
        UPDATE r_resources
        SET reserved = reserved + %(amount)s
        WHERE user_id = %(user_id)s AND
              kind = %(kind)s AND
              interval_started_at = %(interval_started_at)s AND
              used + reserved + %(amount)s <= %(limit)s
        RETURNING *
    """

    results = await execute(sql, {'user_id': user_id,
                                  'kind': kind,
                                  'interval_started_at': interval_started_at,
                                  'amount': amount,
                                  'limit': limit})

    return len(results) > 0
