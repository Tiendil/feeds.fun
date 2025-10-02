from collections import Counter
from typing import Iterable

from ffun.core.postgresql import ExecuteType, execute, run_in_transaction, transaction
from ffun.domain.entities import EntryId, TagId, TagUid
from ffun.ontology import cache, operations
from ffun.ontology.entities import NormalizedTag, Tag, TagCategory, TagPropertyType
from ffun.tags import converters

count_total_tags = operations.count_total_tags
count_total_tags_per_type = operations.count_total_tags_per_type
count_total_tags_per_category = operations.count_total_tags_per_category
count_new_tags_at = operations.count_new_tags_at
tag_frequency_statistics = operations.tag_frequency_statistics


_tags_cache = cache.TagsCache()


async def get_ids_by_uids(tags: Iterable[TagUid]) -> dict[TagUid, TagId]:
    return await _tags_cache.ids_by_uids(tags)


async def get_tags_by_ids(ids: Iterable[TagId]) -> dict[TagId, TagUid]:
    return await _tags_cache.uids_by_ids(ids)


# TODO: in the future we could split this function into two separate functions
#       1. tags & properties normalization
#       2. saving tags & properties to the database
async def apply_tags_to_entry(entry_id: EntryId, processor_id: int, tags: Iterable[NormalizedTag]) -> None:
    """Apply tags to entry.

    Function expects raw tags from processors => after normalization we could have duplicates.
    => Function skips duplicated tags.
    """
    uids = {tag.uid for tag in tags}

    uids_to_ids = await get_ids_by_uids(uids)

    properties = []

    processed_tags = set()

    for tag in tags:
        tag_id = uids_to_ids[tag.uid]

        if tag_id in processed_tags:
            # skip duplicated tags
            continue

        processed_tags.add(tag_id)

        properties.extend(tag.build_properties_for(tag_id, processor_id=processor_id))

    async with transaction() as execute:
        await operations.apply_tags(execute, entry_id, processor_id, uids_to_ids.values())
        await operations.apply_tags_properties(execute, properties)


async def get_tags_ids_for_entries(entries_ids: list[EntryId]) -> dict[EntryId, set[TagId]]:
    return await operations.get_tags_for_entries(execute, entries_ids)


async def get_tags_info(tags_ids: Iterable[TagId]) -> dict[TagId, Tag]:  # noqa: CCR001
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
async def remove_relations_for_entries(execute: ExecuteType, entries_ids: list[EntryId]) -> None:
    relation_ids = await operations.get_relations_for_entries(execute, entries_ids)
    await operations.remove_relations(execute, relation_ids)


@run_in_transaction
async def tech_copy_relations(execute: ExecuteType, entry_from_id: EntryId, entry_to_id: EntryId) -> None:
    await operations.tech_copy_relations(execute, entry_from_id, entry_to_id)


def _inplace_filter_out_entry_tags(
    entry_tag_ids: dict[EntryId, set[TagId]], must_have_tags: set[TagId], min_tag_count: int
) -> set[TagId]:
    """Function modifies `entry_tag_ids` in place and returns a final set of tags that still there."""
    tags_count: Counter[TagId] = Counter()
    for tags in entry_tag_ids.values():
        tags_count.update(tags)

    tags_to_exclude = {tag_id for tag_id, count in tags_count.items() if count < min_tag_count}
    tags_to_exclude -= must_have_tags

    whole_tags = set(tags_count.keys()) - tags_to_exclude

    for entry_tags in entry_tag_ids.values():
        entry_tags.intersection_update(whole_tags)

    return whole_tags


# TODO: tests
async def prepare_tags_for_entries(
    entry_ids: list[EntryId], must_have_tags: set[TagId], min_tag_count: int
) -> tuple[dict[EntryId, set[TagId]], dict[TagId, TagUid]]:

    entry_tag_ids = await get_tags_ids_for_entries(entry_ids)

    whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids, must_have_tags, min_tag_count)

    tag_mapping = await get_tags_by_ids(whole_tags)

    return entry_tag_ids, tag_mapping


@run_in_transaction
async def remove_orphaned_tags(execute: ExecuteType, chunk: int, protected_tags: list[TagId]) -> int:
    orphaned_tags = await operations.get_orphaned_tags(execute, limit=chunk, protected_tags=protected_tags)

    await operations.remove_tags(execute, orphaned_tags)

    # Since we run the code in a transaction, we do nothing with relations here
    # In case some relations will be added during the transaction, we encounter a foreign key violation
    # => the transaction will be rolled back
    # Since the probability of such situation is very low, we can add code to handle such situations
    # later if needed

    return len(orphaned_tags)
