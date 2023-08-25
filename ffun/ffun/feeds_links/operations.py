import uuid
from typing import Any

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.feeds_links.entities import FeedLink

logger = logging.get_module_logger()


def row_to_feed_link(row: dict[str, Any]) -> FeedLink:
    return FeedLink(user_id=row["user_id"], feed_id=row["feed_id"], created_at=row["created_at"])


async def add_link(user_id: uuid.UUID, feed_id: uuid.UUID) -> None:
    sql = """
        INSERT INTO fl_links (id, user_id, feed_id)
        VALUES (%(id)s, %(user_id)s, %(feed_id)s)
        ON CONFLICT (user_id, feed_id) DO NOTHING
    """

    await execute(sql, {"id": uuid.uuid4(), "user_id": user_id, "feed_id": feed_id})


async def remove_link(user_id: uuid.UUID, feed_id: uuid.UUID) -> None:
    sql = """
        DELETE FROM fl_links WHERE user_id = %(user_id)s AND feed_id = %(feed_id)s
    """

    await execute(sql, {"user_id": user_id, "feed_id": feed_id})


async def get_linked_feeds(user_id: uuid.UUID) -> list[FeedLink]:
    sql = """
        SELECT * FROM fl_links WHERE user_id = %(user_id)s
    """

    result = await execute(sql, {"user_id": user_id})

    return [row_to_feed_link(row) for row in result]


async def get_linked_users(feed_id: uuid.UUID) -> list[uuid.UUID]:
    sql = """
        SELECT user_id FROM fl_links WHERE feed_id = %(feed_id)s
    """

    result = await execute(sql, {"feed_id": feed_id})

    return [row["user_id"] for row in result]


async def has_linked_users(feed_id: uuid.UUID) -> bool:
    sql = """
        SELECT 1 FROM fl_links WHERE feed_id = %(feed_id)s LIMIT 1
    """

    result = await execute(sql, {"feed_id": feed_id})

    return bool(result)
