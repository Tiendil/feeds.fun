import uuid
from typing import Iterable

from bidict import bidict

from ffun.core.postgresql import ExecuteType, execute, run_in_transaction, transaction
from ffun.ontology import operations
from ffun.ontology.entities import ProcessorTag, Tag, TagCategory, TagPropertyType
from ffun.tags import converters

_tags_cache: bidict[str, int] = bidict()


async def get_id_by_uid(tag: str) -> int:
    if tag in _tags_cache:
        return _tags_cache[tag]

    tag_id = await operations.get_or_create_id_by_tag(tag)

    _tags_cache[tag] = tag_id

    return tag_id


async def get_ids_by_uids(tags: Iterable[str]) -> dict[str, int]:
    return {tag: await get_id_by_uid(tag) for tag in tags}


async def get_tags_by_ids(ids: Iterable[int]) -> dict[int, str]:
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

    _tags_cache.inverse.update(missed_tags)

    result.update(missed_tags)

    return result


async def apply_tags_to_entry(entry_id: uuid.UUID, processor_id: int, tags: Iterable[ProcessorTag]) -> None:
    raw_to_uids = {tag.raw_uid: converters.normalize(tag.raw_uid) for tag in tags}

    uids_to_ids = await get_ids_by_uids(raw_to_uids.values())

    properties = []

    for tag in tags:
        properties.extend(tag.build_properties_for(uids_to_ids[raw_to_uids[tag.raw_uid]], processor_id=processor_id))

    async with transaction() as execute:
        await operations.apply_tags(execute, entry_id, processor_id, uids_to_ids.values())
        await operations.apply_tags_properties(execute, properties)


async def get_tags_ids_for_entries(entries_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[int]]:
    return await operations.get_tags_for_entries(execute, entries_ids)


async def get_tags_for_entries(entries_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[str]]:
    tags_ids = await operations.get_tags_for_entries(execute, entries_ids)

    all_tags = set()

    for tags in tags_ids.values():
        all_tags.update(tags)

    tags_mapping = await get_tags_by_ids(all_tags)

    result = {entry_id: {tags_mapping[tag_id] for tag_id in tags} for entry_id, tags in tags_ids.items()}

    for entry_id in entries_ids:
        if entry_id not in result:
            result[entry_id] = set()

    return result


async def get_tags_info(tags_ids: Iterable[int]) -> dict[int, Tag]:  # noqa: CCR001
    # we expect that properties will be sorted by date from the newest to the oldest
    properties = await operations.get_tags_properties(tags_ids)

    tags_by_ids = await get_tags_by_ids(tags_ids)

    info = {tag_id: Tag(id=tag_id, name=converters.verbose(tags_by_ids[tag_id])) for tag_id in tags_ids}

    # TODO: implement more complex merging
    for property in properties:
        tag = info[property.tag_id]

        if property.type == TagPropertyType.link:
            if tag.link is None:
                tag.link = property.value
            continue

        if property.type == TagPropertyType.categories:
            tag.categories.update(TagCategory(cat) for cat in property.value.split(","))
            continue

        raise NotImplementedError(f"Unknown property type: {property.type}")

    return info


@run_in_transaction
async def remove_relations_for_entries(execute: ExecuteType, entries_ids: list[uuid.UUID]) -> None:
    await operations.remove_relations_for_entries(execute, entries_ids)


@run_in_transaction
async def tech_copy_relations(execute: ExecuteType, entry_from_id: uuid.UUID, entry_to_id: uuid.UUID) -> None:
    await operations.tech_copy_relations(execute, entry_from_id, entry_to_id)
