import datetime
from typing import Any, Iterable

import psycopg
from pypika import PostgreSQLQuery

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.domain import urls as domain_urls
from ffun.domain.domain import new_source_id
from ffun.domain.entities import SourceId
from ffun.feeds.entities import Feed, FeedError, FeedId, FeedState

logger = logging.get_module_logger()


def row_to_feed(row: dict[str, Any]) -> Feed:
    return Feed(
        id=row["id"],
        source_id=row["source_id"],
        url=row["url"],
        state=FeedState(row["state"]),
        last_error=FeedError(row["last_error"]) if row["last_error"] else None,
        load_attempted_at=row["load_attempted_at"],
        loaded_at=row["loaded_at"],
        title=row["title"],
        description=row["description"],
    )


async def save_feed(feed: Feed) -> FeedId:
    sql = """
    INSERT INTO f_feeds (id, source_id, url, state, title, description, uid)
    VALUES (%(id)s, %(source_id)s, %(url)s, %(state)s, %(title)s, %(description)s, %(uid)s)
    """

    uid = domain_urls.url_to_uid(feed.url)

    try:
        await execute(
            sql,
            {
                "id": feed.id,
                "source_id": feed.source_id,
                "url": feed.url,
                "state": feed.state,
                "title": feed.title,
                "description": feed.description,
                "uid": uid,
            },
        )

        return feed.id
    except psycopg.errors.UniqueViolation as e:
        logger.warning("unique_violation_while_saving_feed", feed=feed)

        result = await execute("SELECT id FROM f_feeds WHERE uid = %(uid)s", {"uid": uid})

        if not result:
            raise NotImplementedError("something went wrong") from e

        return FeedId(result[0]["id"])


@run_in_transaction
async def get_next_feeds_to_load(execute: ExecuteType, number: int, loaded_before: datetime.datetime) -> list[Feed]:
    sql = """
    SELECT id
    FROM f_feeds
    WHERE load_attempted_at IS NULL OR load_attempted_at <= %(loaded_before)s
    ORDER BY load_attempted_at ASC NULLS FIRST
    LIMIT %(number)s
    FOR UPDATE SKIP LOCKED
    """

    rows = await execute(sql, {"number": number, "loaded_before": loaded_before})

    ids = [row["id"] for row in rows]

    sql = """
    UPDATE f_feeds
    SET load_attempted_at = NOW(),
        updated_at = NOW()
    WHERE id = ANY(%(ids)s)
    RETURNING *
    """

    rows = await execute(sql, {"ids": ids})

    return [row_to_feed(row) for row in rows]


async def update_feed_info(feed_id: FeedId, title: str, description: str) -> None:
    sql = """
    UPDATE f_feeds
    SET title = %(title)s,
        description = %(description)s,
        updated_at = NOW()
    WHERE id = %(id)s
    """

    await execute(sql, {"id": feed_id, "title": title, "description": description})


async def mark_feed_as_loaded(feed_id: FeedId) -> None:
    sql = """
    UPDATE f_feeds
    SET state = %(state)s,
        last_error = NULL,
        loaded_at = NOW(),
        updated_at = NOW()
    WHERE id = %(id)s
    """

    await execute(sql, {"id": feed_id, "state": FeedState.loaded})


async def mark_feed_as_failed(feed_id: FeedId, state: FeedState, error: FeedError) -> None:
    sql = """
    UPDATE f_feeds
    SET state = %(state)s,
        last_error = %(error)s,
        updated_at = NOW()
    WHERE id = %(id)s
    """

    await execute(sql, {"id": feed_id, "state": state, "error": error})


async def mark_feed_as_orphaned(feed_id: FeedId) -> None:
    sql = """
    UPDATE f_feeds
    SET state = %(state)s,
        last_error = NULL,
        updated_at = NOW()
    WHERE id = %(id)s
    """

    await execute(sql, {"id": feed_id, "state": FeedState.orphaned})


async def get_feeds(ids: Iterable[FeedId]) -> list[Feed]:
    sql = """
    SELECT *
    FROM f_feeds
    WHERE id = ANY(%(ids)s)
    """

    rows = await execute(sql, {"ids": list(ids)})

    return [row_to_feed(row) for row in rows]


async def get_source_ids(source_uids: Iterable[str]) -> dict[str, SourceId]:

    if not source_uids:
        return {}

    query = PostgreSQLQuery.into("f_sources").columns("id", "uid")

    for source_uid in source_uids:
        query = query.insert(new_source_id(), source_uid)

    query = query.on_conflict("uid").do_nothing()

    await execute(str(query))

    result = await execute(
        "SELECT id, uid FROM f_sources WHERE uid = ANY(%(source_uids)s)", {"source_uids": list(source_uids)}
    )

    return {row["uid"]: row["id"] for row in result}


async def tech_remove_feed(feed_id: FeedId) -> None:
    sql = """
    DELETE FROM f_feeds
    WHERE id = %(feed_id)s
    """

    await execute(sql, {"feed_id": feed_id})


async def count_total_feeds() -> int:
    result = await execute("SELECT COUNT(*) FROM f_feeds")
    return result[0]["count"]  # type: ignore


async def count_total_feeds_per_state() -> dict[FeedState, int]:

    numbers: dict[FeedState, int] = {state: 0 for state in FeedState}

    result = await execute("SELECT state, COUNT(*) FROM f_feeds GROUP BY state")

    for row in result:
        numbers[FeedState(row["state"])] = row["count"]

    return numbers


async def count_total_feeds_per_last_error() -> dict[FeedError, int]:

    numbers: dict[FeedError, int] = {error: 0 for error in FeedError}

    result = await execute("SELECT last_error, COUNT(*) FROM f_feeds GROUP BY last_error")

    for row in result:
        if row["last_error"] is None:
            continue

        numbers[FeedError(row["last_error"])] = row["count"]

    return numbers
