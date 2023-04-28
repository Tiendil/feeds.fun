
import datetime
import uuid

import psycopg
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction

logger = logging.get_module_logger()


async def add_link(user_id: uuid.UUID, feed_id: uuid.UUID):
    sql = """
        INSERT INTO fl_links (id, user_id, feed_id)
        VALUES (%(id)s, %(user_id)s, %(feed_id)s)
        ON CONFLICT (user_id, feed_id) DO NOTHING
    """

    await execute(sql, {'id': uuid.uuid4(), "user_id": user_id, "feed_id": feed_id})


async def remove_link(user_id: uuid.UUID, feed_id: uuid.UUID):
    sql = """
        DELETE FROM fl_links WHERE user_id = %(user_id)s AND feed_id = %(feed_id)s
    """

    await execute(sql, {"user_id": user_id, "feed_id": feed_id})


async def get_linked_feeds(user_id: uuid.UUID) -> list[uuid.UUID]:
    sql = """
        SELECT feed_id FROM fl_links WHERE user_id = %(user_id)s
    """

    result = await execute(sql, {"user_id": user_id})

    return [row["feed_id"] for row in result]
