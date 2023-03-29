
import uuid

import psycopg
from ffun.core.postgresql import execute

from .entities import Feed

sql_insert_feed = '''
INSERT INTO f_feeds (id, url)
VALUES (%(id)s, %(url)s)
ON CONFLICT (id) DO NOTHING
'''


async def save_feeds(feeds: list[Feed]) -> None:

    for feed in feeds:
        try:
            await execute(sql_insert_feed,
                          {'id': uuid.uuid4(), 'url': feed.url})
        except psycopg.errors.UniqueViolation:
            print('something went wrong')
