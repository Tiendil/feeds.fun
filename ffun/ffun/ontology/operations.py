import datetime
import uuid
from typing import Iterable, Sequence

import psycopg
from bidict import bidict
from pypika import PostgreSQLQuery, Table

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import EntryId, TagId, TagUid
from ffun.ontology import errors
from ffun.ontology.entities import TagProperty, TagPropertyType, TagStatsBucket
from ffun.tags.entities import TagCategory

logger = logging.get_module_logger()


o_tags = Table("o_tags")
o_relations = Table("o_relations")
o_tags_properties = Table("o_tags_properties")
o_relations_processors = Table("o_relations_processors")


async def get_tags_mappig() -> bidict[TagUid, TagId]:
    sql = "SELECT id, uid FROM o_tags"
    rows = await execute(sql)
    return bidict.bidict({row["uid"]: row["id"] for row in rows})  # type: ignore


async def get_id_by_tag(tag: TagUid) -> TagId | None:
    sql = "SELECT id FROM o_tags WHERE uid = %(tag)s"
    rows = await execute(sql, {"tag": tag})

    if not rows:
        return None

    return rows[0]["id"]  # type: ignore


async def register_tag(tag: TagUid) -> TagId:
    sql = """
    INSERT INTO o_tags (uid)
    VALUES (%(tag)s)
    ON CONFLICT (uid) DO NOTHING
    RETURNING id"""

    rows = await execute(sql, {"tag": tag})

    if not rows:
        tag_id = await get_id_by_tag(tag)

        assert tag_id is not None
        assert isinstance(tag_id, int)

        return tag_id

    assert isinstance(rows[0]["id"], int)

    return rows[0]["id"]  # type: ignore


async def get_or_create_id_by_tag(tag: TagUid) -> TagId:
    tag_id = await get_id_by_tag(tag)

    if tag_id is not None:
        return tag_id

    return await register_tag(tag)


async def get_tags_by_ids(tags_ids: list[TagId]) -> dict[TagId, TagUid]:
    sql = "SELECT * FROM o_tags WHERE id = ANY(%(tags_ids)s)"
    rows = await execute(sql, {"tags_ids": tags_ids})
    return {row["id"]: row["uid"] for row in rows}


async def _save_tags(execute: ExecuteType, entry_id: EntryId, tags_ids: Iterable[TagId]) -> None:
    if not tags_ids:
        return

    query = PostgreSQLQuery.into(o_relations).columns("entry_id", "tag_id")

    for tag_id in tags_ids:
        query = query.insert(entry_id, tag_id)

    query = query.on_conflict("entry_id", "tag_id").do_nothing()

    await execute(str(query))


async def register_relations_processors(execute: ExecuteType, relations_ids: Iterable[int], processor_id: int) -> None:

    if not relations_ids:
        return

    query = PostgreSQLQuery.into(o_relations_processors).columns("relation_id", "processor_id")

    for relation_id in relations_ids:
        query = query.insert(relation_id, processor_id)

    query = query.on_conflict("relation_id", "processor_id").do_nothing()

    await execute(str(query))


async def apply_tags(execute: ExecuteType, entry_id: EntryId, processor_id: int, tag_ids: list[TagId]) -> None:
    await _save_tags(execute, entry_id, tag_ids)

    relation_ids = await get_relations_for(execute, entry_ids=[entry_id], tag_ids=tag_ids)

    await register_relations_processors(execute, relation_ids, processor_id)


async def apply_tags_properties(execute: ExecuteType, properties: Sequence[TagProperty]) -> None:

    if not properties:
        return

    # check for duplicates
    tags_ids = {(property.tag_id, property.type, property.processor_id) for property in properties}

    if len(tags_ids) != len(properties):
        raise errors.DuplicatedTagPropeties()

    query = PostgreSQLQuery.into(o_tags_properties).columns("tag_id", "type", "value", "processor_id", "created_at")

    # sort properties to avoid deadlocks
    properties = sorted(properties, key=lambda p: (p.tag_id, p.type, p.processor_id))

    for property in properties:
        query = query.insert(
            property.tag_id,
            property.type,
            property.value,
            property.processor_id,
            property.created_at,
        )

    query = query.on_conflict("tag_id", "type", "processor_id").do_update("value")

    await execute(str(query))


async def get_tags_for_entries(execute: ExecuteType, entries_ids: list[EntryId]) -> dict[EntryId, set[TagId]]:
    sql = """SELECT CONCAT(entry_id::text, '|', tag_id::text) AS ids
             FROM o_relations
             WHERE entry_id = ANY(%(entries_ids)s)"""

    rows = await execute(sql, {"entries_ids": entries_ids})

    result: dict[EntryId, set[TagId]] = {}

    entry_ids_mapping: dict[str, EntryId] = {}

    for row in rows:
        raw_entry_id, raw_tag_id = row["ids"].split("|")

        if raw_entry_id not in entry_ids_mapping:
            entry_ids_mapping[raw_entry_id] = EntryId(uuid.UUID(raw_entry_id))

        tag_id = int(raw_tag_id)

        entry_id = entry_ids_mapping[raw_entry_id]

        if entry_id not in result:
            result[entry_id] = set()

        result[entry_id].add(tag_id)  # type: ignore

    return result


async def get_tags_properties(tags_ids: Iterable[TagId]) -> list[TagProperty]:
    result = await execute(
        "SELECT * FROM o_tags_properties WHERE tag_id = ANY(%(tags_ids)s) ORDER BY created_at DESC",
        {"tags_ids": list(tags_ids)},
    )

    return [
        TagProperty(
            tag_id=row["tag_id"],
            type=TagPropertyType(row["type"]),
            value=row["value"],
            processor_id=row["processor_id"],
            created_at=row["created_at"],
        )
        for row in result
    ]


async def remove_relations(execute: ExecuteType, relations_ids: list[int]) -> None:
    sql = "DELETE FROM o_relations_processors WHERE relation_id = ANY(%(relations_ids)s)"

    await execute(sql, {"relations_ids": relations_ids})

    sql = "DELETE FROM o_relations WHERE id = ANY(%(ids)s)"

    await execute(sql, {"ids": relations_ids})


async def count_total_tags() -> int:
    result = await execute("SELECT COUNT(*) FROM o_tags")
    return result[0]["count"]  # type: ignore


async def count_total_tags_per_category() -> dict[TagCategory, int]:

    numbers: dict[TagCategory, int] = {}

    sql = """
    SELECT count(*)
    FROM o_tags_properties
    WHERE type = %(type)s AND value LIKE %(value)s
    """

    for category in TagCategory:
        result = await execute(sql, {"type": TagPropertyType.categories, "value": f"%{category.value}%"})

        numbers[category] = result[0]["count"]

    return numbers


async def count_total_tags_per_type() -> dict[TagPropertyType, int]:

    numbers: dict[TagPropertyType, int] = {type_: 0 for type_ in TagPropertyType}

    sql = """
    SELECT type, count(*)
    FROM o_tags_properties
    GROUP BY type
    """

    result = await execute(sql)

    for row in result:
        numbers[TagPropertyType(row["type"])] = row["count"]

    return numbers


async def count_new_tags_at(date: datetime.date) -> int:
    sql = """
    SELECT COUNT(*) AS count
    FROM o_tags
    WHERE DATE(created_at) = %(date)s
    """

    result = await execute(sql, {"date": date})

    if not result:
        return 0

    return result[0]["count"]  # type: ignore


async def tag_frequency_statistics(buckets: list[int]) -> list[TagStatsBucket]:
    sql = """
WITH
  borders AS (
    SELECT
      b   AS lower_bound,
      LEAD(b) OVER (ORDER BY b) AS upper_bound
    FROM   unnest(%(buckets)s) AS t(b)
  ),
  tag_counts AS (
    SELECT
      tag_id,
      COUNT(*) AS cnt
    FROM   o_relations
    GROUP  BY tag_id
  )
SELECT
  b.lower_bound,
  b.upper_bound,
  COUNT(tc.tag_id) AS tags_count
FROM borders AS b
LEFT JOIN tag_counts AS tc
  ON tc.cnt >= b.lower_bound
 AND (b.upper_bound IS NULL OR tc.cnt < b.upper_bound)
GROUP BY b.lower_bound, b.upper_bound
ORDER BY b.lower_bound;
"""

    result = await execute(sql, {"buckets": buckets})

    stats = [
        TagStatsBucket(
            lower_bound=row["lower_bound"],
            upper_bound=row["upper_bound"],
            count=row["tags_count"],
        )
        for row in result
    ]

    stats.sort(key=lambda b: b.lower_bound)

    return stats


async def get_orphaned_tags(execute: ExecuteType, limit: int, protected_tags: list[TagId]) -> list[TagId]:
    # PostgreSQL planner should recognize the "anti-join" pattern and provide a proper plan
    # if not, we should think about more complex query
    sql = """
SELECT t.id
FROM o_tags AS t
LEFT JOIN o_relations AS r
  ON r.tag_id = t.id
WHERE r.id IS NULL
      AND t.id != ALL(%(protected_tags)s)
LIMIT %(limit)s
    """

    result = await execute(sql, {"protected_tags": protected_tags, "limit": limit})

    return [row["id"] for row in result]


async def remove_tags(execute: ExecuteType, tags_ids: list[TagId]) -> bool:
    if not tags_ids:
        return True

    sql = "DELETE FROM o_tags_properties WHERE tag_id = ANY(%(tags_ids)s)"

    await execute(sql, {"tags_ids": list(tags_ids)})

    sql = "DELETE FROM o_tags WHERE id = ANY(%(tags_ids)s)"

    try:
        await execute(sql, {"tags_ids": list(tags_ids)})
    except psycopg.errors.ForeignKeyViolation:
        logger.warning("unique_violation_while_deleting_tags")
        return False

    return True


async def get_relations_for(
    execute: ExecuteType,
    entry_ids: list[EntryId] | None = None,
    tag_ids: list[TagId] | None = None,
    processor_ids: list[int] | None = None,
) -> list[int]:

    if entry_ids is None and tag_ids is None and processor_ids is None:
        raise errors.AtLeastOneFilterMustBeDefined()

    if entry_ids == [] or tag_ids == [] or processor_ids == []:
        return []

    query = PostgreSQLQuery.from_(o_relations).select("id")

    if entry_ids:
        query = query.where(o_relations.entry_id.isin(list(entry_ids)))

    if tag_ids:
        query = query.where(o_relations.tag_id.isin(list(tag_ids)))

    if processor_ids:
        query = query.left_join(o_relations_processors).on(o_relations.id == o_relations_processors.relation_id)
        query = query.where(o_relations_processors.processor_id.isin(list(processor_ids)))

    result = await execute(str(query))

    return [row["id"] for row in result]


async def copy_relations_to_new_tag(execute: ExecuteType, relation_ids: list[int], new_tag_id: TagId) -> list[int]:
    if not relation_ids:
        return []

    # We use DO UPDATE since we need to return all new relations ids
    sql = """
    INSERT INTO o_relations (entry_id, tag_id)
    SELECT entry_id, %(new_tag_id)s
    FROM o_relations
    WHERE id = ANY(%(relation_ids)s)
    ON CONFLICT (entry_id, tag_id) DO UPDATE SET tag_id = EXCLUDED.tag_id
    RETURNING id
    """

    results = await execute(sql, {"new_tag_id": new_tag_id, "relation_ids": relation_ids})

    return [row["id"] for row in results]


async def copy_tag_properties(execute: ExecuteType, processor_id: int, old_tag_id: TagId, new_tag_id: TagId) -> None:
    sql = """
    INSERT INTO o_tags_properties (tag_id, type, value, processor_id, created_at)
    SELECT %(new_tag_id)s, type, value, processor_id, created_at
    FROM o_tags_properties
    WHERE tag_id = %(old_tag_id)s AND processor_id = %(processor_id)s
    ON CONFLICT (tag_id, type, processor_id) DO NOTHING
    """

    await execute(sql, {"new_tag_id": new_tag_id, "old_tag_id": old_tag_id, "processor_id": processor_id})
