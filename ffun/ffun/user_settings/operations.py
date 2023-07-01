import uuid
from typing import Any, Iterable

from ffun.core import logging
from ffun.core.postgresql import execute

logger = logging.get_module_logger()


async def save_setting(user_id: uuid.UUID,
                       kind: int,
                       value: str) -> None:

    sql = """
        INSERT INTO us_settings (user_id, kind, value)
        VALUES (%(user_id)s, %(kind)s, %(value)s)
        ON CONFLICT (user_id, kind)
        DO UPDATE SET value = %(value)s
    """

    await execute(sql, {'user_id': user_id,
                        'kind': kind,
                        'value': value})


async def load_settings(user_id: uuid.UUID,
                        kinds: Iterable[int]) -> dict[int, str]:

    sql = """
        SELECT *
        FROM us_settings
        WHERE user_id = %(user_id)s
        AND kind = ANY(%(kinds)s)
    """

    result = await execute(sql, {'user_id': user_id,
                                 'kinds': kinds})

    values = {}

    for row in result:
        values[row['kind']] = row['value']

    return values
