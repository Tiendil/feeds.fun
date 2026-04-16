import datetime
import uuid
from typing import Any, AsyncGenerator, Iterable

import psycopg
from psycopg.types.json import Jsonb
from pypika import PostgreSQLQuery

from ffun.core import logging, utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.domain.entities import EntryId, FeedId
from ffun.library import errors
from ffun.library.entities import CollectedEntry, Entry, FeedEntryLink, Reference
from ffun.library.settings import settings

logger = logging.get_module_logger()

# 1. We do not use `published_at` for ordering entries in feeds, because of the following reasons:
#    - Feeds without `published_at` data exist. There is no clear way to handle their ordering.
#    - Feeds can have weird `published_at` values:
#        - in the future, because that's how devs decided to implement "locked head post" in their blog engine.
#        - in the past such as `1970-01-01T00:00:00Z` because devs don't care about `published_at` value.
#        - in wrong format.
#
# 2. We use `ingested_at` as the mark of actuality of feed entries, see comments
#    in `catalog_entries` and `_catalog_entry` for details.
#
# 3. We use `l_entries.created_at` (and its copy `l_feeds_to_entries.entry_created_at`)
#    for sorting and filtering entries, see comments in `catalog_entries` and `_catalog_entry` for details.
#
# Note: currently we have too manu indexes on `l_feeds_to_entries`, there ways to reduce their number
#       but they require some hacks:
#       - We can replace l_feeds_to_entries.created_at with l_feeds_to_entries.entry_created_at in queries
#         because for most sources (sites) they should be nearly equal to the actual publish date
#       - We can remove index on `ingested_at` in favor of getting the link with the latest `created_at`
#         and using its `ingested_at`.


def dict_to_reference(row: dict[str, Any]) -> Reference:
    return Reference(
        semantics=row["semantics"],
        url=row["url"],
        title=row.get("title"),
        mime_type=row.get("mime_type"),
        width=row.get("width"),
        height=row.get("height"),
        duration=row.get("duration"),
        size=row.get("size"),
        extra=row.get("extra"),
    )


def row_to_entry(row: dict[str, Any]) -> Entry:
    return Entry(
        id=row["id"],
        source_id=row["source_id"],
        title=row["title"],
        body=row["body"],
        external_id=row["external_id"],
        external_url=row["external_url"],
        external_tags=row["external_tags"],
        published_at=row["published_at"],
        created_at=row["created_at"],
        references=[dict_to_reference(ref) for ref in row["refs"]],
    )


@run_in_transaction
async def _catalog_entry(
    execute: ExecuteType, feed_id: FeedId, entry: CollectedEntry, ingested_at: datetime.datetime
) -> bool:
    sql_insert_entry = """
    INSERT INTO l_entries (id, source_id, title, body, external_id, external_url, external_tags, published_at, refs)
    VALUES (%(id)s, %(source_id)s, %(title)s, %(body)s, %(external_id)s,
            %(external_url)s, %(external_tags)s, %(published_at)s, %(refs)s)
    ON CONFLICT (source_id, external_id) DO NOTHING
    RETURNING id, created_at
    """

    # 1. We expect that `entry_created_at` is constant.
    #    However, we update it on conflict, just in case (we always have it).
    #
    # 2. We need `enty_created_at` as a fixed published_at date for feed entries to use in the HTTP API
    #    without it we forced to use MIN(l_feeds_to_entries.created_at) which is specific to the concrete user
    #    => HTTP API can not always determine the best published_at value for entry
    #    => that overcomplicates API.
    #
    # 3. We can use `entry_created_at` safely enough because entry is unique per source
    #    (source is a site, blog, etc.)
    #    => we expect that entry will appear in feeds from the same source at the same time
    #    We MUST to rethink that approach in case we'll make feed source wider
    #    (for example, by uniting multiple sites), that is unlikely for now
    #    => the simplicity of the HTTP API has priority over idiomaticity of the DB schema and semantics
    sql_insert_feed_to_entry = """
    INSERT INTO l_feeds_to_entries (feed_id, entry_id, ingested_at, entry_created_at)
    VALUES (%(feed_id)s, %(entry_id)s, %(ingested_at)s, %(entry_created_at)s)
    ON CONFLICT (feed_id, entry_id) DO UPDATE SET
      ingested_at = EXCLUDED.ingested_at,
      entry_created_at = EXCLUDED.entry_created_at
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
            "refs": Jsonb(
                [ref.model_dump(mode="json", exclude_defaults=True, exclude_none=True) for ref in entry.references]
            ),
        },
    )

    new_entry_created: bool

    if result:
        new_entry_created = True
        entry_id = result[0]["id"]
        entry_created_at = result[0]["created_at"]
    else:
        new_entry_created = False
        result = await execute(
            "SELECT id, created_at FROM l_entries WHERE source_id = %(source_id)s AND external_id = %(external_id)s",
            {"source_id": entry.source_id, "external_id": entry.external_id},
        )

        if result:
            entry_id = result[0]["id"]
            entry_created_at = result[0]["created_at"]
        else:
            raise NotImplementedError("Can not find entry by source_id and external_id")

    await execute(
        sql_insert_feed_to_entry,
        {"feed_id": feed_id, "entry_id": entry_id, "ingested_at": ingested_at, "entry_created_at": entry_created_at},
    )

    return new_entry_created


async def catalog_entries(feed_id: FeedId, entries: Iterable[CollectedEntry]) -> int:

    # We MUST use the same `ingested_at` value for all entries ingested in the same load
    # to be able to use `ingested_at` as a marker/version of ingested bunch of entries
    ingested_at = utils.now()

    count = 0

    # 1. We use the time of the last ingestion as the marker of actuality of the feed entries.
    #    We use that maker to decide which entries can be safely unlinked from the feed.
    #    => We should update `ingested_at` for all entries in the feed on each load, even if entry is not new.
    #
    # 2. We expect that entries list is sorted by the feed source in some reasonable way to
    #    represent publishing order (from new to old). It is important, because we use `l_entries.created_at`
    #    (and its denormalized copy in `l_feeds_to_entries.entry_created_at`) for filtering and sorting
    #    entries.
    #    => We catalog entries in reversed order, so the oldest entry will have the oldest `created_at`.
    for entry in reversed(list(entries)):
        if await _catalog_entry(feed_id, entry, ingested_at):
            count += 1

    return count


async def get_feed_links_for_entries(
    execute: ExecuteType, entries_ids: Iterable[EntryId]
) -> dict[EntryId, list[FeedEntryLink]]:
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
        period = settings.max_entry_age

    # 1. Check comments in `_catalog_entry` function for details.
    #
    # 2. We can not sort by `published_at` because it is absolutely unreliable
    #
    # 3. We can do `DISTINCT entry_id, entry_created_at` because `entry_created_at` is constant
    sql = """
    SELECT le.*
    FROM (
        SELECT DISTINCT entry_id, entry_created_at
        FROM l_feeds_to_entries
        WHERE entry_created_at > NOW() - %(period)s
          AND feed_id = ANY(%(feeds_ids)s)
        ORDER BY entry_created_at DESC, entry_id DESC
        LIMIT %(limit)s
    ) AS picked
    LEFT JOIN l_entries AS le ON le.id = picked.entry_id
    ORDER BY created_at DESC, entry_id DESC
    """

    rows = await execute(sql, {"feeds_ids": feeds_ids, "period": period, "limit": limit})

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


async def get_last_ingested_at(execute: ExecuteType, feed_id: FeedId) -> datetime.datetime | None:
    sql = """
    SELECT MAX(ingested_at) AS last_ingested_at
    FROM l_feeds_to_entries
    WHERE feed_id = %(feed_id)s
    """

    result = await execute(sql, {"feed_id": feed_id})

    if not result:
        return None

    last_ingested_at = result[0]["last_ingested_at"]
    assert last_ingested_at is None or isinstance(last_ingested_at, datetime.datetime)
    return last_ingested_at


async def unlink_feed_tail(execute: ExecuteType, feed_id: FeedId, offset: int | None = None) -> set[EntryId]:
    """Ensure that feed contains no more than `offset` entries."""
    if offset is None:
        offset = settings.max_entries_per_feed

    if offset < settings.min_entries_per_feed:
        raise errors.FeedHeadIsTooShort()

    # We use `last_ingested_at` to protect entries ingested on the last feed load
    last_ingested_at = await get_last_ingested_at(execute, feed_id)

    if last_ingested_at is None:
        logger.info("feed_has_no_entries", feed_id=feed_id)
        return set()

    # We sort by `created_at` instead of `<ingested_at, created_at>`
    # because from the user's perspective the entry that appeared earlier should be removed earlier too
    sql = """
    WITH tail AS MATERIALIZED (
        SELECT feed_id, entry_id
        FROM l_feeds_to_entries
        WHERE feed_id = %(feed_id)s
        ORDER BY created_at DESC, entry_id DESC
        OFFSET %(offset)s
    )
    DELETE FROM l_feeds_to_entries
    USING tail
    WHERE l_feeds_to_entries.feed_id = tail.feed_id
      AND l_feeds_to_entries.entry_id = tail.entry_id
      AND l_feeds_to_entries.ingested_at < %(last_ingested_at)s
    RETURNING l_feeds_to_entries.entry_id AS entry_id
    """

    result = await execute(sql, {"feed_id": feed_id, "offset": offset, "last_ingested_at": last_ingested_at})

    if not result:
        logger.info("feed_has_no_entries_tail", feed_id=feed_id, entries_limit=offset)
        return set()

    logger.info("feed_entries_tail_removed", feed_id=feed_id, entries_limit=offset, entries_removed=len(result))

    return {row["entry_id"] for row in result}


async def unlink_all(execute: ExecuteType, feed_id: FeedId) -> set[EntryId]:
    sql = """
    DELETE FROM l_feeds_to_entries
    WHERE feed_id = %(feed_id)s
    RETURNING entry_id
    """

    result = await execute(sql, {"feed_id": feed_id})

    if not result:
        logger.info("feed_has_no_entries", feed_id=feed_id)
        return set()

    unlinked = {row["entry_id"] for row in result}

    await try_mark_as_orphanes(execute, unlinked)

    logger.info("feed_entries_removed", feed_id=feed_id, entries_removed=len(result))

    return unlinked


async def unlink_old_entries(
    execute: ExecuteType, feed_id: FeedId, period: datetime.timedelta | None = None
) -> set[EntryId]:
    """Ensure that feed contains no entries older than `period`."""
    if period is None:
        period = settings.max_entry_age

    # We use `last_ingested_at` to protect entries ingested on the last feed load
    last_ingested_at = await get_last_ingested_at(execute, feed_id)

    if last_ingested_at is None:
        logger.info("feed_has_no_entries", feed_id=feed_id)
        return set()

    # We sort by `created_at` because from the user's perspective
    # the entry that appeared earlier should be removed earlier too
    sql = """
    WITH protected AS MATERIALIZED (
        SELECT entry_id
        FROM l_feeds_to_entries
        WHERE feed_id = %(feed_id)s
        ORDER BY created_at DESC, entry_id DESC
        LIMIT %(min_entries_per_feed)s
    ),
    old_rows AS MATERIALIZED (
        SELECT feed_id, entry_id
        FROM l_feeds_to_entries
        WHERE feed_id = %(feed_id)s AND created_at < NOW() - %(period)s
    )
    DELETE FROM l_feeds_to_entries
    USING old_rows
    WHERE l_feeds_to_entries.feed_id = old_rows.feed_id
      AND l_feeds_to_entries.entry_id = old_rows.entry_id
      AND l_feeds_to_entries.ingested_at < %(last_ingested_at)s
      AND NOT EXISTS (
          SELECT 1
          FROM protected
          WHERE protected.entry_id = old_rows.entry_id
      )
    RETURNING l_feeds_to_entries.entry_id AS entry_id
    """

    result = await execute(
        sql,
        {
            "feed_id": feed_id,
            "period": period,
            "min_entries_per_feed": settings.min_entries_per_feed,
            "last_ingested_at": last_ingested_at,
        },
    )

    if not result:
        logger.info("feed_has_no_old_entries", feed_id=feed_id, old_period=period)
        return set()

    logger.info("feed_old_entries_removed", feed_id=feed_id, old_period=period, entries_removed=len(result))

    return {row["entry_id"] for row in result}


# TODO: metrics for orphaned entries and for feeds that produce them
async def try_mark_as_orphanes(execute: ExecuteType, entry_ids: set[EntryId]) -> None:
    if not entry_ids:
        return

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
