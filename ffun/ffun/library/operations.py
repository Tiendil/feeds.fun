import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

import psycopg
from pypika import PostgreSQLQuery

from ffun.core import logging, utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.domain.entities import EntryId, FeedId
from ffun.library import errors
from ffun.library.entities import CollectedEntry, Entry, FeedEntryLink, PersonalizedEntry
from ffun.library.settings import settings

logger = logging.get_module_logger()


def row_to_entry(row: dict[str, Any]) -> Entry:
    row.pop("created_at", None)
    return Entry(**row)


def row_to_personalized_entry(row: dict[str, Any]) -> PersonalizedEntry:
    row.pop("created_at", None)
    return PersonalizedEntry(**row)


@run_in_transaction
async def _catalog_entry(execute: ExecuteType, feed_id: FeedId, entry: CollectedEntry) -> bool:
    sql_insert_entry = """
    INSERT INTO l_entries (id, source_id, title, body, external_id, external_url, external_tags, published_at)
    VALUES (%(id)s, %(source_id)s, %(title)s, %(body)s, %(external_id)s,
            %(external_url)s, %(external_tags)s, %(published_at)s)
    ON CONFLICT (source_id, external_id) DO NOTHING
    RETURNING id
    """

    # 1. We update `published_at` in case of link exists but published_at is different
    #    This logic works in pair with check for old entries in `catalog_entries`
    #    so the actual logic is "only update published_at if the new value is in acceptable lifetime range`
    #    it is as intended.
    #    This logic is required to better handle the case when the feed updates the published_at for the entry
    #    but we remove it because the previous published_at is too old, which leads to reprocessing of the same entry
    #    and we don't want that.
    # 2. The current logic introduces a weird behaviour when the feeds contains two exemples of the same entry.
    #    In that case the last one will overwrite the published_at for the previous one.
    #    That is not what we may want, but it should be a very rare case.
    sql_insert_feed_to_entry = """
    INSERT INTO l_feeds_to_entries (feed_id, entry_id, published_at)
    VALUES (%(feed_id)s, %(entry_id)s, %(published_at)s)
    ON CONFLICT (feed_id, entry_id) DO UPDATE
    SET published_at = EXCLUDED.published_at
    WHERE l_feeds_to_entries.published_at IS DISTINCT FROM EXCLUDED.published_at
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

    new_entry_created: bool

    if result:
        new_entry_created = True
        entry_id = result[0]["id"]
    else:
        new_entry_created = False
        result = await execute(
            "SELECT id FROM l_entries WHERE source_id = %(source_id)s AND external_id = %(external_id)s",
            {"source_id": entry.source_id, "external_id": entry.external_id},
        )

        if result:
            entry_id = result[0]["id"]
        else:
            raise NotImplementedError("Can not find entry by source_id and external_id")

    await execute(sql_insert_feed_to_entry, {"feed_id": feed_id, "entry_id": entry_id, "published_at": entry.published_at})

    return new_entry_created


async def catalog_entries(feed_id: FeedId, entries: Iterable[CollectedEntry]) -> int:
    count = 0

    for entry in entries:
        if entry.published_at < utils.now() - settings.max_entry_age:
            # hard protection from storing old entries
            continue

        if await _catalog_entry(feed_id, entry):
            count += 1

    return count


async def get_feed_links_for_entries(
    execute: ExecuteType, entries_ids: Iterable[EntryId]
) -> dict[EntryId, list[FeedEntryLink]]:
    sql = """
    SELECT entry_id, feed_id, published_at, created_at
    FROM l_feeds_to_entries
    WHERE entry_id = ANY(%(entries_ids)s)
    """

    result = await execute(sql, {"entries_ids": list(entries_ids)})

    feeds_for_entries: dict[EntryId, list[FeedEntryLink]] = {}

    for row in result:
        entry_id = row["entry_id"]
        feed_id = row["feed_id"]
        published_at = row["published_at"]
        created_at = row["created_at"]

        if entry_id not in feeds_for_entries:
            feeds_for_entries[entry_id] = []

        feeds_for_entries[entry_id].append(
            FeedEntryLink(feed_id=feed_id,
                          entry_id=entry_id,
                          published_at=published_at,
                          created_at=created_at))

    return feeds_for_entries


async def get_entries_by_ids(ids: Iterable[EntryId]) -> dict[EntryId, Entry | None]:

    sql_select_entries = """SELECT * FROM l_entries WHERE id = ANY(%(ids)s)"""

    rows = await execute(sql_select_entries, {"ids": ids})

    result: dict[EntryId, Entry | None] = {id: None for id in ids}

    for row in rows:
        result[row["id"]] = row_to_entry(row)

    return result


async def get_entries_by_filter(
    feeds_ids: Iterable[FeedId], limit: int, period: datetime.timedelta | None = None
) -> list[PersonalizedEntry]:
    if period is None:
        period = settings.max_entry_age

    # 1. Here is an important logic implemented
    #    When we are applying published time restriction
    #    we are looking at a time of entry publishing in a requested feeds,
    #    not the published time from the entry itself
    #    In most cases, those times should be nearly the same, but there is a possibility
    #    that there will be aggregator-style feeds that include old entries as new.
    #    In such cases, we'll show such an entry as new to a user.
    #    We may want to change this logic in the future.
    #
    # 2. Also, we order by two fields (published_at and created_at) to work around the case
    #    when published_at is the same for several entries
    #
    # 3. Outer sorting uses entry_id to ensure deterministic order
    #    when there are multiple entries with the same published_at and created_at
    sql = """
    SELECT le.*, picked.published_at as picked_published_at, picked.created_at as picked_created_at
    FROM (
        SELECT DISTINCT ON (entry_id) entry_id, published_at, created_at
        FROM l_feeds_to_entries
        WHERE published_at > NOW() - %(period)s
          AND feed_id = ANY(%(feeds_ids)s)
        ORDER BY entry_id, published_at DESC, created_at DESC
    ) AS picked
    JOIN l_entries AS le ON le.id = picked.entry_id
    ORDER BY picked.picked_published_at DESC, picked.picked_created_at DESC, picked.entry_id DESC
    LIMIT %(limit)s
    """

    rows = await execute(sql, {"feeds_ids": feeds_ids, "period": period, "limit": limit})

    for row in rows:
        # We ensure that `published_at` is specific for feeds, not for global load history
        # So the user will see the entry as published at the time when the user could see it in their feeds
        # not at the time when the entry was published by some other feed that the user does not follow.
        row["published_at"] = row.pop("picked_published_at")

    return [row_to_personalized_entry(row) for row in rows]


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


async def unlink_feed_tail(execute: ExecuteType, feed_id: FeedId, offset: int | None = None) -> None:

    if offset is None:
        offset = settings.max_entries_per_feed

    # TODO: refactor to use https://www.psycopg.org/psycopg3/docs/api/cursors.html#psycopg.Cursor.rowcount
    # We use `created_at` as a second sorting field to ensure that tail will be detected correctly
    # in the case when the feeds sets equal `published_at` for several entries.
    sql = """
    WITH cte AS (
        SELECT feed_id, entry_id
        FROM l_feeds_to_entries
        WHERE feed_id = %(feed_id)s
        ORDER BY published_at DESC, created_at DESC
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

    await try_mark_as_orphanes(execute, potential_orphanes)


async def unlink_old_entries(execute: ExecuteType, feed_id: FeedId, period: datetime.timedelta | None = None) -> None:

    if period is None:
        period = settings.max_entry_age

    sql = """
    WITH cte AS (
        SELECT feed_id, entry_id
        FROM l_feeds_to_entries
        WHERE feed_id = %(feed_id)s AND published_at < NOW() - %(period)s
    )
    DELETE FROM l_feeds_to_entries
    USING cte
    WHERE l_feeds_to_entries.feed_id = cte.feed_id
      AND l_feeds_to_entries.entry_id = cte.entry_id
    RETURNING l_feeds_to_entries.entry_id AS entry_id
    """

    result = await execute(sql, {"feed_id": feed_id, "period": period})

    if not result:
        logger.info("feed_has_no_old_entries", feed_id=feed_id, old_period=period)
        return

    logger.info("feed_old_entries_removed", feed_id=feed_id, old_period=period, entries_removed=len(result))

    potential_orphanes = [row["entry_id"] for row in result]

    await try_mark_as_orphanes(execute, potential_orphanes)


# TODO: metrics for orphaned entries and for feeds that produce them
async def try_mark_as_orphanes(execute: ExecuteType, entry_ids: Iterable[EntryId]) -> None:
    feed_links = await get_feed_links_for_entries(execute, entry_ids)

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


async def sync_orphaned_entries() -> None:
    """Detect entries that are no longer orphaned and remove them from orphaned entries table."""
    sql = """
    DELETE FROM l_orphaned_entries AS oe
    USING l_feeds_to_entries AS fe
    WHERE oe.entry_id = fe.entry_id
    """

    await execute(sql)


async def remove_entries_by_ids(execute: ExecuteType, entry_ids: Iterable[EntryId]) -> None:
    ids = list(entry_ids)

    try:
        await execute("DELETE FROM l_feeds_to_entries WHERE entry_id = ANY(%(ids)s)", {"ids": ids})
        await execute("DELETE FROM l_entries WHERE id = ANY(%(ids)s)", {"ids": ids})
        await execute("DELETE FROM l_orphaned_entries WHERE entry_id = ANY(%(ids)s)", {"ids": ids})
    except psycopg.errors.ForeignKeyViolation as e:
        logger.warning("foreign_key_violation_on_entry_removal", entry_ids=ids)
        raise errors.ConcurentOperationOnRemovedEntries() from e


async def count_total_entries() -> int:
    result = await execute("SELECT COUNT(*) FROM l_entries")
    return result[0]["count"]  # type: ignore
