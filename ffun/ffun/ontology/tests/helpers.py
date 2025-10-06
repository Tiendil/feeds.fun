from typing import Iterable

from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId, TagId
from ffun.ontology.operations import get_tags_for_entries


async def assert_has_tags(tags_ids: dict[EntryId, Iterable[int]]) -> None:
    tags = await get_tags_for_entries(execute, [entry_id for entry_id in tags_ids])

    for entry_id, tag_ids in tags_ids.items():
        assert tags.get(entry_id, set()) >= set(tag_ids)


async def unexisting_tag_id() -> int:
    result = await execute(
        "SELECT MAX(id) AS mx FROM o_tags",
    )

    if not result or result[0]["mx"] is None:
        return 1

    return result[0]["mx"] + 1  # type: ignore


async def get_relation_signatures(relation_ids: list[int]) -> list[tuple[EntryId, TagId, int | None]]:
    sql = """
    SELECT r.entry_id, r.tag_id, rp.processor_id
    FROM o_relations AS r
    LEFT JOIN o_relations_processors AS rp ON r.id = rp.relation_id
    WHERE r.id = ANY(%(ids)s)
    ORDER BY r.entry_id, r.tag_id, rp.processor_id
    """

    result = await execute(sql, {"ids": relation_ids})

    return [(row["entry_id"], row["tag_id"], row["processor_id"]) for row in result]
