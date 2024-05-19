import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

import psycopg

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.library import errors
from ffun.library.entities import Entry

logger = logging.get_module_logger()


sql_insert_entry = """
INSERT INTO l_entries (id, feed_id, title, body,
                       external_id, external_url, external_tags, published_at)
VALUES (%(id)s, %(feed_id)s, %(title)s, %(body)s,
        %(external_id)s, %(external_url)s, %(external_tags)s, %(published_at)s)
"""


def row_to_entry(row: dict[str, Any]) -> Entry:
    row["cataloged_at"] = row.pop("created_at")
    return Entry(**row)


async def catalog_entries(entries: Iterable[Entry]) -> None:
    for entry in entries:
        try:
            await execute(
                sql_insert_entry,
                {
                    "id": entry.id,
                    "feed_id": entry.feed_id,
                    "title": entry.title,
                    "body": entry.body,
                    "external_id": entry.external_id,
                    "external_url": entry.external_url,
                    "external_tags": list(entry.external_tags),
                    "published_at": entry.published_at,
                },
            )
        except psycopg.errors.UniqueViolation:
            logger.warning("racing_is_possible_unique_violation_while_saving_entry", entry_id=entry.id)


# we must controll unique constraint on entries by pair feed + id because
# 1. we can not guarantee that there will be no duplicates of feeds
#    (can not guarantee perfect normalization of urls, etc)
# 2. someone can damage database by infecting with wrong entries from faked feed
async def check_stored_entries_by_external_ids(feed_id: uuid.UUID, external_ids: Iterable[str]) -> set[str]:
    sql = """
    SELECT external_id
    FROM l_entries
    WHERE feed_id = %(feed_id)s AND external_id = ANY(%(external_ids)s)
    """

    rows = await execute(sql, {"external_ids": external_ids, "feed_id": feed_id})

    return {row["external_id"] for row in rows}


sql_select_entries = """SELECT * FROM l_entries WHERE id = ANY(%(ids)s)"""


async def get_entries_by_ids(ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Entry | None]:
    rows = await execute(sql_select_entries, {"ids": ids})

    result: dict[uuid.UUID, Entry | None] = {id: None for id in ids}

    for row in rows:
        result[row["id"]] = row_to_entry(row)

    return result


async def get_entries_by_filter(
    feeds_ids: Iterable[uuid.UUID], limit: int, period: datetime.timedelta | None = None
) -> list[Entry]:
    if period is None:
        period = datetime.timedelta(days=100 * 365)

    sql = """
    SELECT * FROM l_entries
    WHERE created_at > NOW() - %(period)s and feed_id = ANY(%(feeds_ids)s)
    ORDER BY created_at DESC
    LIMIT %(limit)s"""

    rows = await execute(sql, {"feeds_ids": feeds_ids, "period": period, "limit": limit})

    return [row_to_entry(row) for row in rows]


async def get_entries_after_pointer(
    created_at: datetime.datetime, entry_id: uuid.UUID, limit: int
) -> list[tuple[uuid.UUID, datetime.datetime]]:
    # Indenx on created_at should be enough (currently it is (created_at, feed_idid))
    # In case of troubles we could add index on (created_at, id)
    sql = """
    SELECT id, created_at FROM l_entries
    WHERE created_at > %(created_at)s OR
          (created_at = %(created_at)s AND id > %(entry_id)s)
    ORDER BY created_at ASC, id ASC
    LIMIT %(limit)s
    """

    rows = await execute(sql, {"created_at": created_at, "entry_id": entry_id, "limit": limit})

    return [(row["id"], row["created_at"]) for row in rows]


# iterate by pairs (feed_id, entry_id) because we already have index on it
# TODO: rewrite to use get_entries_after_pointer
async def all_entries_iterator(chunk: int) -> AsyncGenerator[Entry, None]:
    feed_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    entry_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    sql = """
    SELECT * FROM l_entries
    WHERE (%(feed_id)s, %(entry_id)s) < (feed_id, id)
    ORDER BY feed_id, id ASC
    LIMIT %(chunk)s
    """

    while True:
        rows = await execute(sql, {"feed_id": feed_id, "entry_id": entry_id, "chunk": chunk})

        if not rows:
            break

        for row in rows:
            yield row_to_entry(row)

        feed_id = rows[-1]["feed_id"]
        entry_id = rows[-1]["id"]


async def update_external_url(entity_id: uuid.UUID, url: str) -> None:
    sql = """
    UPDATE l_entries
    SET external_url = %(url)s
    WHERE id = %(entity_id)s
    """

    await execute(sql, {"entity_id": entity_id, "url": url})


async def tech_remove_entries_by_ids(entries_ids: Iterable[uuid.UUID]) -> None:
    sql = """
    DELETE FROM l_entries
    WHERE id = ANY(%(entries_ids)s)
    """

    await execute(sql, {"entries_ids": list(entries_ids)})


async def tech_move_entry(entry_id: uuid.UUID, feed_id: uuid.UUID) -> None:
    sql = """
    UPDATE l_entries
    SET feed_id = %(feed_id)s
    WHERE id = %(entry_id)s
    """

    try:
        await execute(sql, {"entry_id": entry_id, "feed_id": feed_id})
    except psycopg.errors.UniqueViolation as e:
        raise errors.CanNotMoveEntryAlreadyInFeed(entry_id=entry_id, feed_id=feed_id) from e


async def tech_get_feed_entries_tail(feed_id: uuid.UUID, offset: int) -> set[uuid.UUID]:
    """
    Get the last entries for the feed.
    """
    # Order by published_at because we want to keep the newest entries
    # and it is better to take decission based on time from an entry's source rather than on time when we collected it
    sql = """
    SELECT id
    FROM l_entries
    WHERE feed_id = %(feed_id)s
    ORDER BY published_at DESC
    OFFSET %(offset)s
    """

    result = await execute(sql, {"feed_id": feed_id, "offset": offset})

    return {row["id"] for row in result}
