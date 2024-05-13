import uuid
from typing import Iterable

from ffun.core.postgresql import execute
from ffun.ontology.operations import get_tags_for_entries


async def assert_has_tags(tags_ids: dict[uuid.UUID, Iterable[int]]) -> None:
    tags = await get_tags_for_entries(execute, [entry_id for entry_id in tags_ids])

    for entry_id, tag_ids in tags_ids.items():
        assert tags.get(entry_id, set()) >= set(tag_ids)
