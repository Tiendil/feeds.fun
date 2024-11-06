import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

from pypika import PostgreSQLQuery

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.domain.entities import EntryId, FeedId
from ffun.library.entities import Entry, FeedEntryLink
from ffun.library.settings import settings

logger = logging.get_module_logger()


def row_to_entry(row: dict[str, Any]) -> Entry:
    row["cataloged_at"] = row.pop("created_at")
    return Entry(**row)


@run_in_transaction
async def _catalog_entry(execute: ExecuteType, feed_id: FeedId, entry: Entry) -> None:
    sql_insert_entry = """
    INSERT INTO l_entries (id, source_id, title, body, external_id, external_url, external_tags, published_at)
    VALUES (%(id)s, %(source_id)s, %(title)s, %(body)s, %(external_id)s,
            %(external_url)s, %(external_tags)s, %(published_at)s)
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
        result = await execute(
            "SELECT id FROM l_entries WHERE source_id = %(source_id)s AND external_id = %(external_id)s",
            {"source_id": entry.source_id, "external_id": entry.external_id},
        )

        if result:
            entry_id = result[0]["id"]
        else:
            raise NotImplementedError("Can not find entry by source_id and external_id")

    await execute(sql_insert_feed_to_entry, {"feed_id": feed_id, "entry_id": entry_id})


async def catalog_entries(feed_id: FeedId, entries: Iterable[Entry]) -> None:
    for entry in entries:
        await _catalog_entry(feed_id, entry)


async def get_feed_links_for_entries(entries_ids: Iterable[EntryId]) -> dict[EntryId, list[FeedEntryLink]]:
    sql = """
    SELECT entry_id, feed_id, created_at
    FROM l_feeds_to_entries
    WHERE entry_id = ANY(%(entries_ids)s)
    """

    result = await execute(sql, {"entries_ids": list(entries_ids)})

    feeds_for_entries: dict[EntryId, list[FeedEntryLink]] = {}

    for row in result:
        entry_id = row["entry_id"]
        feed_id = row["feed_id"]
        created_at = row["created_at"]

        if entry_id not in feeds_for_entries:
            feeds_for_entries[entry_id] = []

        feeds_for_entries[entry_id].append(FeedEntryLink(feed_id=feed_id, entry_id=entry_id, created_at=created_at))

    return feeds_for_entries


async def find_stored_entries_for_feed(feed_id: FeedId, external_ids: Iterable[str]) -> set[str]:

    sql = """
    SELECT external_id
    FROM l_entries
    JOIN l_feeds_to_entries ON l_entries.id = l_feeds_to_entries.entry_id
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


async def get_entries_by_filter(
    feeds_ids: Iterable[FeedId], limit: int, period: datetime.timedelta | None = None
) -> list[Entry]:
    if period is None:
        period = datetime.timedelta(days=100 * 365)

    # Here is an important logic implemented
    # When we are applying created time restriction
    # we are looking at a time of creating a link between entry and feed, not the real cataloged time
    # In most cases, those times should be nearly the same, but there is a possibility
    # that there will be aggregator-style feeds that include old entries as new.
    # In such cases, we'll show such an entry as new to a user.
    # We may want to change this logic in the future.

    sql = """
    SELECT le.*, re.max_created_at
    FROM (
        SELECT lfe.entry_id AS id, MAX(lfe.created_at) AS max_created_at
        FROM l_feeds_to_entries AS lfe
        WHERE lfe.created_at > NOW() - %(period)s
          AND lfe.feed_id = ANY(%(feeds_ids)s)
        GROUP BY lfe.entry_id
        ORDER BY MAX(lfe.created_at) DESC
        LIMIT %(limit)s
    ) AS re
    JOIN l_entries AS le ON le.id = re.id
    ORDER BY re.max_created_at DESC;
    """

    rows = await execute(sql, {"feeds_ids": feeds_ids, "period": period, "limit": limit})

    for row in rows:
        row.pop("max_created_at")

    return [row_to_entry(row) for row in rows]


async def get_entries_after_pointer(
    created_at: datetime.datetime, entry_id: EntryId, limit: int
) -> list[tuple[EntryId, datetime.datetime]]:
    sql = """
    SELECT id, created_at FROM l_entries
    WHERE created_at > %(created_at)s OR
          (created_at = %(created_at)s AND id > %(entry_id)s)
    ORDER BY created_at ASC, id ASC
    LIMIT %(limit)s
    """

    rows = await execute(sql, {"created_at": created_at, "entry_id": entry_id, "limit": limit})

    return [(row["id"], row["created_at"]) for row in rows]


# TODO: rewrite to use get_entries_after_pointer
async def all_entries_iterator(chunk: int) -> AsyncGenerator[Entry, None]:
    entry_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    sql = """
    SELECT * FROM l_entries
    WHERE %(entry_id)s < id
    ORDER BY id ASC
    LIMIT %(chunk)s
    """

    while True:
        rows = await execute(sql, {"entry_id": entry_id, "chunk": chunk})

        if not rows:
            break

        for row in rows:
            yield row_to_entry(row)

        entry_id = rows[-1]["id"]


async def update_external_url(entity_id: EntryId, url: str) -> None:
    sql = """
    UPDATE l_entries
    SET external_url = %(url)s
    WHERE id = %(entity_id)s
    """

    await execute(sql, {"entity_id": entity_id, "url": url})


async def unlink_feed_tail(feed_id: FeedId, offset: int | None = None) -> None:

    if offset is None:
        offset = settings.max_entries_per_feed

    # TODO: refactor to use https://www.psycopg.org/psycopg3/docs/api/cursors.html#psycopg.Cursor.rowcount
    sql = """
    WITH cte AS (
        SELECT feed_id, entry_id
        FROM l_feeds_to_entries
        WHERE feed_id = %(feed_id)s
        ORDER BY created_at DESC
        OFFSET %(offset)s
    )
    DELETE FROM l_feeds_to_entries
    USING cte
    WHERE l_feeds_to_entries.feed_id = cte.feed_id
      AND l_feeds_to_entries.entry_id = cte.entry_id
    RETURNING l_feeds_to_entries.entry_id AS entry_id
    """

    result = await execute(sql, {"feed_id": feed_id, "offset": offset})

    if not result:
        logger.info("feed_has_no_entries_tail", feed_id=feed_id, entries_limit=offset)
        return

    logger.info("feed_entries_tail_removed", feed_id=feed_id, entries_limit=offset, entries_removed=len(result))

    potential_orphanes = [row["entry_id"] for row in result]

    await try_mark_as_orphanes(potential_orphanes)


# TODO: metrics for orphaned entries and for feeds that produce them
async def try_mark_as_orphanes(entry_ids: Iterable[EntryId]) -> None:
    feed_links = await get_feed_links_for_entries(entry_ids)

    orphans = [entry_id for entry_id in entry_ids if entry_id not in feed_links]

    if not orphans:
        return

    query = PostgreSQLQuery.into("l_orphaned_entries").columns("entry_id")

    for entry_id in orphans:
        query = query.insert(entry_id)

    query = query.on_conflict("entry_id").do_nothing()

    await execute(str(query))


async def get_orphaned_entries(limit: int) -> set[EntryId]:
    sql = """
    SELECT entry_id
    FROM l_orphaned_entries
    LIMIT %(limit)s
    """

    rows = await execute(sql, {"limit": limit})

    return {row["entry_id"] for row in rows}


@run_in_transaction
async def remove_entries_by_ids(execute: ExecuteType, entry_ids: Iterable[EntryId]) -> None:
    ids = list(entry_ids)

    await execute("DELETE FROM l_feeds_to_entries WHERE entry_id = ANY(%(ids)s)", {"ids": ids})
    await execute("DELETE FROM l_entries WHERE id = ANY(%(ids)s)", {"ids": ids})
    await execute("DELETE FROM l_orphaned_entries WHERE entry_id = ANY(%(ids)s)", {"ids": ids})


async def count_total_entries() -> int:
    result = await execute("SELECT COUNT(*) FROM l_entries")
    return result[0]["count"]  # type: ignore
