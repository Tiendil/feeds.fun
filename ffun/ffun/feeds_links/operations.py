import uuid
from typing import Any, Iterable

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import UserId
from ffun.feeds.entities import FeedId
from ffun.feeds_collections.collections import collections
from ffun.feeds_links.entities import FeedLink

logger = logging.get_module_logger()


def row_to_feed_link(row: dict[str, Any]) -> FeedLink:
    return FeedLink(user_id=row["user_id"], feed_id=row["feed_id"], created_at=row["created_at"])


async def add_link(user_id: UserId, feed_id: FeedId) -> None:
    sql = """
        INSERT INTO fl_links (id, user_id, feed_id)
        VALUES (%(id)s, %(user_id)s, %(feed_id)s)
        ON CONFLICT (user_id, feed_id) DO NOTHING
    """

    await execute(sql, {"id": uuid.uuid4(), "user_id": user_id, "feed_id": feed_id})

    logger.business_event("feed_linked", user_id=user_id, feed_id=feed_id, in_collection=collections.has_feed(feed_id))


async def remove_link(user_id: UserId, feed_id: FeedId) -> None:
    sql = """
        DELETE FROM fl_links WHERE user_id = %(user_id)s AND feed_id = %(feed_id)s
    """

    await execute(sql, {"user_id": user_id, "feed_id": feed_id})

    logger.business_event(
        "feed_unlinked", user_id=user_id, feed_id=feed_id, in_collection=collections.has_feed(feed_id)
    )


async def get_linked_feeds(user_id: UserId) -> list[FeedLink]:
    sql = """
        SELECT * FROM fl_links WHERE user_id = %(user_id)s
    """

    result = await execute(sql, {"user_id": user_id})

    return [row_to_feed_link(row) for row in result]


async def get_link(user_id: UserId, feed_id: FeedId) -> FeedLink | None:
    sql = """
        SELECT * FROM fl_links WHERE user_id = %(user_id)s AND feed_id = %(feed_id)s
    """

    result = await execute(sql, {"user_id": user_id, "feed_id": feed_id})

    if not result:
        return None

    return row_to_feed_link(result[0])


async def get_linked_users(feed_ids: Iterable[FeedId]) -> dict[FeedId, set[UserId]]:
    sql = """
        SELECT feed_id, user_id FROM fl_links WHERE feed_id = ANY(%(feed_ids)s)
    """

    result = await execute(sql, {"feed_ids": list(feed_ids)})

    users: dict[FeedId, set[UserId]] = {}

    for row in result:
        feed_id = row["feed_id"]
        user_id = row["user_id"]

        if feed_id not in users:
            users[feed_id] = set()

        users[feed_id].add(user_id)

    return users


async def has_linked_users(feed_id: FeedId) -> bool:
    sql = """
        SELECT 1 FROM fl_links WHERE feed_id = %(feed_id)s LIMIT 1
    """

    result = await execute(sql, {"feed_id": feed_id})

    return bool(result)


async def count_feeds_per_user() -> dict[UserId, int]:
    sql = """
        SELECT user_id, COUNT(*) FROM fl_links GROUP BY user_id
    """

    result = await execute(sql)

    return {row["user_id"]: row["count"] for row in result}


async def count_subset_feeds_per_user(feed_ids: list[FeedId]) -> dict[UserId, int]:
    sql = """
        SELECT user_id, COUNT(*) FROM fl_links WHERE feed_id = ANY(%(collection_feed_ids)s) GROUP BY user_id
    """

    result = await execute(sql, {"collection_feed_ids": feed_ids})

    return {row["user_id"]: row["count"] for row in result}


async def tech_merge_feeds(execute: ExecuteType, from_feed_id: FeedId, to_feed_id: FeedId) -> None:
    sql = """
    DELETE FROM fl_links as fll
    WHERE feed_id = %(from_feed_id)s
          AND EXISTS (SELECT 1 FROM fl_links WHERE feed_id = %(to_feed_id)s AND user_id = fll.user_id)
    """

    await execute(sql, {"from_feed_id": from_feed_id, "to_feed_id": to_feed_id})

    sql = """
    UPDATE fl_links
    SET feed_id = %(to_feed_id)s
    WHERE feed_id = %(from_feed_id)s
    """

    await execute(sql, {"from_feed_id": from_feed_id, "to_feed_id": to_feed_id})
