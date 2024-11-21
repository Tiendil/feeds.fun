import uuid
from typing import Iterable, Sequence

from bidict import bidict
from pypika import PostgreSQLQuery

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import EntryId
from ffun.ontology import errors
from ffun.ontology.entities import TagCategory, TagProperty, TagPropertyType

logger = logging.get_module_logger()


async def get_tags_mappig() -> bidict[str, int]:
    sql = "SELECT id, uid FROM o_tags"
    rows = await execute(sql)
    return bidict.bidict({row["uid"]: row["id"] for row in rows})  # type: ignore


async def get_id_by_tag(tag: str) -> int | None:
    sql = "SELECT id FROM o_tags WHERE uid = %(tag)s"
    rows = await execute(sql, {"tag": tag})

    if not rows:
        return None

    assert isinstance(rows[0]["id"], int)

    return rows[0]["id"]


async def register_tag(tag: str) -> int:
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

    return rows[0]["id"]


async def get_or_create_id_by_tag(tag: str) -> int:
    tag_id = await get_id_by_tag(tag)

    if tag_id is not None:
        return tag_id

    return await register_tag(tag)


async def get_tags_by_ids(tags_ids: list[int]) -> dict[int, str]:
    sql = "SELECT * FROM o_tags WHERE id = ANY(%(tags_ids)s)"
    rows = await execute(sql, {"tags_ids": tags_ids})
    return {row["id"]: row["uid"] for row in rows}


async def _save_tags(execute: ExecuteType, entry_id: EntryId, tags_ids: Iterable[int]) -> None:
    sql_relations = """
    INSERT INTO o_relations (entry_id, tag_id)
    VALUES (%(entry_id)s, %(tag_id)s)
    ON CONFLICT (entry_id, tag_id) DO NOTHING"""

    for tag_id in tags_ids:
        await execute(sql_relations, {"entry_id": entry_id, "tag_id": tag_id})


async def _register_relations_processors(
    execute: ExecuteType, relations_ids: Iterable[int], processor_id: int
) -> None:
    sql_register_processor = """
    INSERT INTO o_relations_processors (relation_id, processor_id)
    VALUES (%(relation_id)s, %(processor_id)s)
    ON CONFLICT (relation_id, processor_id) DO NOTHING"""

    for relation_id in relations_ids:
        await execute(sql_register_processor, {"relation_id": relation_id, "processor_id": processor_id})


async def _get_relations_for_entry_and_tags(
    execute: ExecuteType, entry_id: EntryId, tags_ids: Iterable[int]
) -> dict[int, int]:
    result = await execute(
        "SELECT id, tag_id FROM o_relations WHERE entry_id = %(entry_id)s AND tag_id = ANY(%(tags_ids)s)",
        {"entry_id": entry_id, "tags_ids": list(tags_ids)},
    )

    return {row["tag_id"]: row["id"] for row in result}


async def apply_tags(execute: ExecuteType, entry_id: EntryId, processor_id: int, tags_ids: Iterable[int]) -> None:
    await _save_tags(execute, entry_id, tags_ids)

    relations = await _get_relations_for_entry_and_tags(execute, entry_id, tags_ids)

    await _register_relations_processors(execute, list(relations.values()), processor_id)


async def tech_copy_relations(execute: ExecuteType, entry_from_id: EntryId, entry_to_id: EntryId) -> None:
    """Copy relations with processors info."""
    # get processors for each tag in entry_from
    sql = """
    SELECT rp.processor_id, r.tag_id
    FROM o_relations_processors rp
    JOIN o_relations r ON rp.relation_id = r.id
    WHERE r.entry_id = %(entry_id)s
    """

    result = await execute(sql, {"entry_id": entry_from_id})

    tags_by_processors: dict[int, list[int]] = {}

    for row in result:
        if row["processor_id"] not in tags_by_processors:
            tags_by_processors[row["processor_id"]] = []

        tags_by_processors[row["processor_id"]].append(row["tag_id"])

    for processor_id, tags_ids in tags_by_processors.items():
        await apply_tags(execute, entry_to_id, processor_id, tags_ids)


async def apply_tags_properties(execute: ExecuteType, properties: Sequence[TagProperty]) -> None:

    if not properties:
        return

    # check for duplicates
    tags_ids = {(property.tag_id, property.type, property.processor_id) for property in properties}

    if len(tags_ids) != len(properties):
        raise errors.DuplicatedTagPropeties()

    query = PostgreSQLQuery.into("o_tags_properties").columns("tag_id", "type", "value", "processor_id", "created_at")

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


async def get_tags_for_entries(execute: ExecuteType, entries_ids: list[EntryId]) -> dict[EntryId, set[int]]:
    sql = """SELECT CONCAT(entry_id::text, '|', tag_id::text) AS ids
             FROM o_relations
             WHERE entry_id = ANY(%(entries_ids)s)"""

    rows = await execute(sql, {"entries_ids": entries_ids})

    result: dict[EntryId, set[int]] = {}

    entry_ids_mapping: dict[str, EntryId] = {}

    for row in rows:
        raw_entry_id, raw_tag_id = row["ids"].split("|")

        if raw_entry_id not in entry_ids_mapping:
            entry_ids_mapping[raw_entry_id] = EntryId(uuid.UUID(raw_entry_id))

        tag_id = int(raw_tag_id)

        entry_id = entry_ids_mapping[raw_entry_id]

        if entry_id not in result:
            result[entry_id] = set()

        result[entry_id].add(tag_id)

    return result


async def get_tags_properties(tags_ids: Iterable[int]) -> list[TagProperty]:
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


async def remove_relations_for_entries(execute: ExecuteType, entries_ids: list[EntryId]) -> None:
    sql = "SELECT id FROM o_relations WHERE entry_id = ANY(%(entries_ids)s)"

    result = await execute(sql, {"entries_ids": entries_ids})

    relations_ids = [row["id"] for row in result]

    sql = "DELETE FROM o_relations_processors WHERE relation_id = ANY(%(relations_ids)s)"

    await execute(sql, {"relations_ids": relations_ids})

    sql = "DELETE FROM o_relations WHERE entry_id = ANY(%(entries_ids)s)"

    await execute(sql, {"entries_ids": entries_ids})


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
