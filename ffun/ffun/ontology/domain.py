
import uuid

import bidict

from . import operations

_tags_cache: bidict[str, int] = bidict()


async def get_id_by_tag(tag: str) -> int:
    if tag in _tags_cache:
        return _tags_cache[tag]

    tag_id = await operations.get_or_create_id_by_tag(tag)

    _tags_cache[tag] = tag_id

    return tag_id


async def get_ids_by_tags(tags: list[str]) -> dict[str, int]:
    return {tag: await get_id_by_tag(tag) for tag in tags}


async def get_tags_by_ids(ids: list[int]) -> dict[int, str]:
    result = {}

    tags_to_request = []

    for tag_id in ids:
        if tag_id in _tags_cache.inverse:
            result[tag_id] = _tags_cache.inverse[tag_id]
        else:
            tags_to_request.append(tag_id)

    if not tags_to_request:
        return result

    missed_tags = await operations.get_tags_by_ids(tags_to_request)

    _tags_cache.update(missed_tags)

    result.update(missed_tags)

    return result


async def apply_tags(entry_id: uuid.UUID,
                     tags: list[str]) -> None:

    tags_ids = await get_ids_by_tags(tags)

    await operations.apply_tags(entry_id, tags_ids.values())
