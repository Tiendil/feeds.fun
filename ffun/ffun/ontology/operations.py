import uuid
from typing import Iterable

import psycopg
from bidict import bidict

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.ontology.entities import Tag, TagProperty, TagPropertyType


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


async def apply_tags(execute: ExecuteType, entry_id: uuid.UUID, processor_id: int, tags_ids: Iterable[int]) -> None:
    sql_relations = """
    INSERT INTO o_relations (entry_id, tag_id)
    VALUES (%(entry_id)s, %(tag_id)s)
    ON CONFLICT (entry_id, tag_id) DO NOTHING"""

    for tag_id in tags_ids:
        await execute(sql_relations, {"entry_id": entry_id, "tag_id": tag_id})

    result = await execute(
        "SELECT id FROM o_relations WHERE entry_id = %(entry_id)s AND tag_id = ANY(%(tags_ids)s)",
        {"entry_id": entry_id, "tags_ids": list(tags_ids)},
    )

    sql_register_processor = """
    INSERT INTO o_relations_processors (relation_id, processor_id)
    VALUES (%(relation_id)s, %(processor_id)s)
    ON CONFLICT (relation_id, processor_id) DO NOTHING"""

    for row in result:
        await execute(sql_register_processor, {"relation_id": row["id"], "processor_id": processor_id})


async def apply_tags_properties(execute: ExecuteType, properties: Iterable[TagProperty]) -> None:
    sql = """
    INSERT INTO o_tags_properties (tag_id, type, value, processor_id, created_at)
    VALUES (%(tag_id)s, %(type)s, %(value)s, %(processor_id)s, %(created_at)s)
    ON CONFLICT (tag_id, type, processor_id) DO UPDATE SET value = %(value)s
    """

    for property in properties:
        await execute(
            sql,
            {
                "tag_id": property.tag_id,
                "type": property.type,
                "value": property.value,
                "processor_id": property.processor_id,
                "created_at": property.created_at,
            },
        )


async def get_tags_for_entries(entries_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[int]]:
    sql = """SELECT * FROM o_relations WHERE entry_id = ANY(%(entries_ids)s)"""

    rows = await execute(sql, {"entries_ids": entries_ids})

    result: dict[uuid.UUID, set[int]] = {}

    for row in rows:
        entry_id = row["entry_id"]
        tag_id = row["tag_id"]

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
