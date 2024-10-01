# noqa
# TODO: remove ^
import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

import psycopg

from ffun.core import logging
from ffun.core.postgresql import execute, transaction, run_in_transaction, ExecuteType
from ffun.domain.entities import EntryId, FeedId, SourceId
from ffun.library import errors
from ffun.library.entities import Entry, FeedEntryLink

logger = logging.get_module_logger()


def row_to_entry(row: dict[str, Any]) -> Entry:
    row["cataloged_at"] = row.pop("created_at")
    return Entry(**row)


@run_in_transaction
async def _catalog_entry(execute: ExecuteType, feed_id: FeedId, entry: Entry) -> None:
    sql_insert_entry = """
    INSERT INTO l_entries (id, source_id, title, body, external_id, external_url, external_tags, published_at)
    VALUES (%(id)s, %(source_id)s, %(title)s, %(body)s, %(external_id)s, %(external_url)s, %(external_tags)s, %(published_at)s)
    ON CONFLICT (source_id, external_id) DO NOTHING
    RETURNING id
    """

    sql_insert_feed_to_entry = """
    INSERT INTO l_feeds_to_entries (feed_id, entry_id)
    VALUES (%(feed_id)s, %(entry_id)s)
    ON CONFLICT (feed_id, entry_id) DO NOTHING
    """

    result = await execute(
        sql_insert_entry,
        {
            "id": entry.id,
            "source_id": entry.source_id,
            "title": entry.title,
            "body": entry.body,
            "external_id": entry.external_id,
            "external_url": entry.external_url,
            "external_tags": list(entry.external_tags),
            "published_at": entry.published_at,
        },
    )

    if result:
        entry_id = result[0]["id"]
    else:
        result = await execute("SELECT id FROM l_entries WHERE source_id = %(source_id)s AND external_id = %(external_id)s",
                               {"source_id": entry.source_id,
                                "external_id": entry.external_id})

        if result:
            entry_id = result[0]["id"]
        else:
            raise NotImplementedError("Can not find entry by source_id and external_id")

    await execute(
        sql_insert_feed_to_entry,
        {
            "feed_id": feed_id,
            "entry_id": entry_id
        })


async def catalog_entries(feed_id: FeedId, entries: Iterable[Entry]) -> None:
    for entry in entries:
        await _catalog_entry(feed_id, entry)


# TODO: tests
# TODO: index?
async def get_feed_entry_links(entries_ids: Iterable[EntryId]) -> dict[EntryId, list[FeedEntryLink]]:
    sql = """
    SELECT entry_id, feed_id, created_at
    FROM l_feeds_to_entries
    WHERE entry_id = ANY(%(entries_ids)s)
    ORDER BY created_at ASC
    """

    result = await execute(sql, {"entries_ids": list(entries_ids)})

    feeds_for_entries = {}

    for row in result:
        entry_id = row["entry_id"]
        feed_id = row["feed_id"]
        created_at = row["created_at"]

        if entry_id not in feeds_for_entries:
            feeds_for_entries[entry_id] = []

        feeds_for_entries[entry_id].append(FeedEntryLink(feed_id=feed_id, entry_id=entry_id, created_at=created_at))

    return feeds_for_entries


# TODO: rename tests
# TODO: test for multiple feeds
async def find_stored_entries_for_feed(feed_id: FeedId, external_ids: Iterable[str]) -> set[str]:

    # TODO: index
    sql = """
    SELECT external_id
    FROM l_entries AS le
    JOIN l_feeds_to_entries AS lfe
    WHERE feed_id = %(feed_id)s AND external_id = ANY(%(external_ids)s)
    """

    rows = await execute(sql, {"external_ids": external_ids, "feed_id": feed_id})

    return {row["external_id"] for row in rows}


async def get_entries_by_ids(ids: Iterable[EntryId]) -> dict[EntryId, Entry | None]:

    sql_select_entries = """SELECT * FROM l_entries WHERE id = ANY(%(ids)s)"""

    rows = await execute(sql_select_entries, {"ids": ids})

    result: dict[EntryId, Entry | None] = {id: None for id in ids}

    for row in rows:
        result[row["id"]] = row_to_entry(row)

    return result


# TODO: test of multiple feeds
# TODO: test of intersection of feeds
async def get_entries_by_filter(
    feeds_ids: Iterable[FeedId], limit: int, period: datetime.timedelta | None = None
) -> list[Entry]:
    if period is None:
        period = datetime.timedelta(days=100 * 365)

    sql = """
    SELECT DISTINCT le.*
    FROM l_entries AS le
    JOIN l_feeds_to_entries AS lfe ON le.id = lfe.entry_id
    WHERE lfe.created_at > NOW() - %(period)s AND lfe.feed_id = ANY(%(feeds_ids)s)
    ORDER BY le.created_at DESC
    LIMIT %(limit)s;
    """

    rows = await execute(sql, {"feeds_ids": feeds_ids, "period": period, "limit": limit})

    return [row_to_entry(row) for row in rows]


async def get_entries_after_pointer(
    created_at: datetime.datetime, entry_id: EntryId, limit: int
) -> list[tuple[EntryId, datetime.datetime]]:
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


async def update_external_url(entity_id: EntryId, url: str) -> None:
    sql = """
    UPDATE l_entries
    SET external_url = %(url)s
    WHERE id = %(entity_id)s
    """

    await execute(sql, {"entity_id": entity_id, "url": url})


@run_in_transaction
async def tech_remove_entries_by_ids(execute: ExecuteType, entries_ids: Iterable[EntryId]) -> None:
    ids = list(entries_ids)

    await execute("DELETE FROM l_feeds_to_entries WHERE entry_idid = ANY(%(entries_ids)s)", {"entries_ids": ids})
    await execute("DELETE FROM l_entries WHERE id = ANY(%(entries_ids)s)", {"entries_ids": ids})


# TODO: no more correct logic, refactor whole call chain
# Async def tech_move_entry(entry_id: EntryId, feed_id: FeedId) -> None:
#     sql = """
#     UPDATE l_entries
#     SET feed_id = %(feed_id)s
#     WHERE id = %(entry_id)s
#     """

#     try:
#         await execute(sql, {"entry_id": entry_id, "feed_id": feed_id})
#     except psycopg.errors.UniqueViolation as e:
#         raise errors.CanNotMoveEntryAlreadyInFeed(entry_id=entry_id, feed_id=feed_id) from e


# TODO: no more correct logic, refactor whole call chain
# async def tech_get_feed_entries_tail(feed_id: FeedId, offset: int) -> set[EntryId]:
#     """
#     Get the last entries for the feed.
#     """
#     # Order by published_at because we want to keep the newest entries
#     # and it is better to take decission based on time from an entry's source rather than on time when we collected it
#     sql = """
#     SELECT id
#     FROM l_entries
#     WHERE feed_id = %(feed_id)s
#     ORDER BY published_at DESC
#     OFFSET %(offset)s
#     """

#     result = await execute(sql, {"feed_id": feed_id, "offset": offset})

#     return {row["id"] for row in result}
