import uuid

import pytest

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import Delta, TableSizeDelta, TableSizeNotChanged
from ffun.domain.entities import EntryId
from ffun.library.entities import Entry
from ffun.ontology import errors
from ffun.ontology.domain import apply_tags_to_entry
from ffun.ontology.entities import ProcessorTag, TagCategory, TagPropertyType
from ffun.ontology.operations import (
    _get_relations_for_entry_and_tags,
    _register_relations_processors,
    _save_tags,
    apply_tags,
    apply_tags_properties,
    count_total_tags,
    count_total_tags_per_category,
    count_total_tags_per_type,
    get_or_create_id_by_tag,
    get_tags_properties,
    remove_relations_for_entries,
    tech_copy_relations,
)
from ffun.ontology.tests.helpers import assert_has_tags


async def assert_tags_processors(entry_id: EntryId, tag_processors: dict[int, set[int]]) -> None:
    relations = await _get_relations_for_entry_and_tags(execute, entry_id, list(tag_processors.keys()))

    relations_ids = list(relations.values())

    sql = "SELECT relation_id, processor_id FROM o_relations_processors WHERE relation_id = ANY(%(relations_ids)s)"

    result = await execute(sql, {"relations_ids": relations_ids})

    expected = set()

    for tag_id, processor_ids in tag_processors.items():
        for processor_id in processor_ids:
            expected.add((relations[tag_id], processor_id))

    assert expected == {(row["relation_id"], row["processor_id"]) for row in result}


class TestSaveTags:
    @pytest.mark.asyncio
    async def test_no_tags(self, cataloged_entry: Entry) -> None:
        async with TableSizeNotChanged("o_relations"):
            await _save_tags(execute, cataloged_entry.id, [])

    @pytest.mark.asyncio
    async def test(
        self, cataloged_entry: Entry, another_cataloged_entry: Entry, three_tags_ids: tuple[int, int, int]
    ) -> None:
        async with TableSizeDelta("o_relations", delta=4):
            await _save_tags(execute, cataloged_entry.id, three_tags_ids[:2])
            await _save_tags(execute, another_cataloged_entry.id, three_tags_ids[1:])

        await assert_has_tags(
            {
                cataloged_entry.id: {three_tags_ids[0], three_tags_ids[1]},
                another_cataloged_entry.id: {three_tags_ids[1], three_tags_ids[2]},
            }
        )


class TestRegisterRelationsProcessors:
    @pytest.mark.asyncio
    async def test_no_relations(self, fake_processor_id: int) -> None:
        async with TableSizeNotChanged("o_relations_processors"):
            await _register_relations_processors(execute, [], fake_processor_id)

    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry, fake_processor_id: int, three_tags_ids: tuple[int, int, int]) -> None:
        await _save_tags(execute, cataloged_entry.id, three_tags_ids[:2])

        relations = await _get_relations_for_entry_and_tags(execute, cataloged_entry.id, three_tags_ids[:2])

        async with TableSizeDelta("o_relations_processors", delta=2):
            await _register_relations_processors(
                execute, relations_ids=list(relations.values()), processor_id=fake_processor_id
            )

        await assert_tags_processors(
            entry_id=cataloged_entry.id,
            tag_processors={three_tags_ids[0]: {fake_processor_id}, three_tags_ids[1]: {fake_processor_id}},
        )

    @pytest.mark.asyncio
    async def test_duplicated(
        self, cataloged_entry: Entry, fake_processor_id: int, three_tags_ids: tuple[int, int, int]
    ) -> None:
        await _save_tags(execute, cataloged_entry.id, three_tags_ids)

        relations = await _get_relations_for_entry_and_tags(execute, cataloged_entry.id, three_tags_ids)

        relation_ids = list(relations.values())

        async with TableSizeDelta("o_relations_processors", delta=3):
            await _register_relations_processors(
                execute, relations_ids=relation_ids[:2], processor_id=fake_processor_id
            )
            await _register_relations_processors(
                execute, relations_ids=relation_ids[1:], processor_id=fake_processor_id
            )

        await assert_tags_processors(
            entry_id=cataloged_entry.id,
            tag_processors={
                three_tags_ids[0]: {fake_processor_id},
                three_tags_ids[1]: {fake_processor_id},
                three_tags_ids[2]: {fake_processor_id},
            },
        )


class TestGetRelationsForEntryAndTags:
    """Tested in other tests & code."""


class TestTechCopyRelations:
    @pytest.mark.asyncio
    async def test_no_relations(self, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        async with TableSizeNotChanged("o_relations"):
            await tech_copy_relations(execute, cataloged_entry.id, another_cataloged_entry.id)

    @pytest.mark.asyncio
    async def test_full_copy(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[int, int, int],
    ) -> None:
        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tags_ids=three_tags_ids[:2]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tags_ids=three_tags_ids[1:]
            )

        async with (
            TableSizeDelta("o_relations_processors", delta=4),
            TableSizeDelta("o_relations", delta=3),
            TableSizeNotChanged("o_tags"),
        ):
            async with transaction() as trx:
                await tech_copy_relations(trx, cataloged_entry.id, another_cataloged_entry.id)

        await assert_has_tags({another_cataloged_entry.id: set(three_tags_ids)})

        await assert_tags_processors(
            entry_id=another_cataloged_entry.id,
            tag_processors={
                three_tags_ids[0]: {fake_processor_id},
                three_tags_ids[1]: {fake_processor_id, another_fake_processor_id},
                three_tags_ids[2]: {another_fake_processor_id},
            },
        )

    @pytest.mark.asyncio
    async def test_some_relations_exist(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[int, int, int],
    ) -> None:
        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tags_ids=three_tags_ids[:2]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tags_ids=three_tags_ids[1:]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=another_cataloged_entry.id, processor_id=fake_processor_id, tags_ids=[three_tags_ids[1]]
            )

        async with (
            TableSizeDelta("o_relations_processors", delta=3),
            TableSizeDelta("o_relations", delta=2),
            TableSizeNotChanged("o_tags"),
        ):
            async with transaction() as trx:
                await tech_copy_relations(trx, cataloged_entry.id, another_cataloged_entry.id)

        await assert_has_tags({another_cataloged_entry.id: set(three_tags_ids)})

        await assert_tags_processors(
            entry_id=another_cataloged_entry.id,
            tag_processors={
                three_tags_ids[0]: {fake_processor_id},
                three_tags_ids[1]: {fake_processor_id, another_fake_processor_id},
                three_tags_ids[2]: {another_fake_processor_id},
            },
        )


class TestRemoveRelationsForEntries:
    @pytest.mark.asyncio
    async def test_nothing_to_remove(self, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        async with TableSizeNotChanged("o_relations"):
            await remove_relations_for_entries(execute, [cataloged_entry.id, another_cataloged_entry.id])

    @pytest.mark.asyncio
    async def test_success(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[int, int, int],
    ) -> None:
        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tags_ids=three_tags_ids[:2]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tags_ids=three_tags_ids[1:]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=another_cataloged_entry.id, processor_id=fake_processor_id, tags_ids=three_tags_ids
            )

        async with transaction() as trx:
            await apply_tags(
                trx,
                entry_id=another_cataloged_entry.id,
                processor_id=another_fake_processor_id,
                tags_ids=three_tags_ids,
            )

        async with (
            TableSizeDelta("o_relations_processors", delta=-4),
            TableSizeDelta("o_relations", delta=-3),
            TableSizeNotChanged("o_tags"),
        ):
            async with transaction() as trx:
                await remove_relations_for_entries(trx, [cataloged_entry.id])

        await assert_has_tags({cataloged_entry.id: set(), another_cataloged_entry.id: set(three_tags_ids)})

        await assert_tags_processors(entry_id=cataloged_entry.id, tag_processors={})

        await assert_tags_processors(
            entry_id=another_cataloged_entry.id,
            tag_processors={
                three_tags_ids[0]: {fake_processor_id, another_fake_processor_id},
                three_tags_ids[1]: {fake_processor_id, another_fake_processor_id},
                three_tags_ids[2]: {fake_processor_id, another_fake_processor_id},
            },
        )


class TestApplyTagsProperties:

    @pytest.mark.asyncio
    async def test_no_properties(self) -> None:
        async with TableSizeNotChanged("o_tags_properties"):
            await apply_tags_properties(execute, [])

    @pytest.mark.asyncio
    async def test_first_time_save(
        self,
        three_tags_by_uids: dict[str, int],
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
        fake_processor_id: int,
    ) -> None:

        properties = []

        for tag in three_processor_tags:
            tag.link = f"https://example.com?{tag.raw_uid}"
            properties.extend(
                tag.build_properties_for(tag_id=three_tags_by_uids[tag.raw_uid], processor_id=fake_processor_id)
            )

        async with TableSizeDelta("o_tags_properties", delta=3):
            await apply_tags_properties(execute, properties)

        loaded_tags_properties = await get_tags_properties(three_tags_by_uids.values())

        loaded_tags_properties.sort(key=lambda x: x.tag_id)
        properties.sort(key=lambda x: x.tag_id)

        assert loaded_tags_properties == properties

    @pytest.mark.asyncio
    async def test_save_duplicated(
        self,
        three_tags_by_uids: dict[str, int],
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
        fake_processor_id: int,
    ) -> None:

        properties = []

        for tag in three_processor_tags:
            tag.link = f"https://example.com?{tag.raw_uid}"
            properties.extend(
                tag.build_properties_for(tag_id=three_tags_by_uids[tag.raw_uid], processor_id=fake_processor_id)
            )

        async with TableSizeDelta("o_tags_properties", delta=3):
            await apply_tags_properties(execute, properties)

        changed_properties = [
            properties[0].replace(),
            properties[1].replace(value="https://example.com?another-uid"),
            properties[2].replace(),
        ]

        async with TableSizeNotChanged("o_tags_properties"):
            await apply_tags_properties(execute, changed_properties)

        loaded_tags_properties = await get_tags_properties(three_tags_by_uids.values())

        loaded_tags_properties.sort(key=lambda x: x.tag_id)
        properties.sort(key=lambda x: x.tag_id)

        assert loaded_tags_properties != properties
        assert loaded_tags_properties == changed_properties

    @pytest.mark.asyncio
    async def test_error_on_duplicated_properties(
        self,
        three_tags_by_uids: dict[str, int],
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
        fake_processor_id: int,
    ) -> None:

        properties = []

        for tag in three_processor_tags:
            tag.link = f"https://example.com?{tag.raw_uid}"
            properties.extend(
                tag.build_properties_for(tag_id=three_tags_by_uids[tag.raw_uid], processor_id=fake_processor_id)
            )

        properties.append(properties[0])

        async with TableSizeNotChanged("o_tags_properties"):
            with pytest.raises(errors.DuplicatedTagPropeties):
                await apply_tags_properties(execute, properties)


class TestCountTotalTags:
    @pytest.mark.asyncio
    async def test_no_tags(self) -> None:
        async with Delta(count_total_tags, delta=3):
            for _ in range(3):
                await get_or_create_id_by_tag(uuid.uuid4().hex)


class TestCountTotalTagsPerCategory:

    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry) -> None:
        tags = [uuid.uuid4().hex for _ in range(5)]

        processor_tags = [
            ProcessorTag(raw_uid=tags[0]),
            ProcessorTag(raw_uid=tags[1], categories={TagCategory.network_domain}),
            ProcessorTag(raw_uid=tags[2], categories={TagCategory.feed_tag}),
            ProcessorTag(raw_uid=tags[3], categories={TagCategory.network_domain, TagCategory.feed_tag}),
            ProcessorTag(raw_uid=tags[4], categories={TagCategory.feed_tag}),
        ]

        numbers_before = await count_total_tags_per_category()

        await apply_tags_to_entry(cataloged_entry.id, 1, processor_tags)

        numbers_after = await count_total_tags_per_category()

        assert numbers_after[TagCategory.network_domain] == numbers_before[TagCategory.network_domain] + 2
        assert numbers_after[TagCategory.feed_tag] == numbers_before[TagCategory.feed_tag] + 3


class TestCountTotalTagsPerType:

    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry) -> None:
        tags = [uuid.uuid4().hex for _ in range(5)]

        processor_tags = [
            ProcessorTag(raw_uid=tags[0]),
            ProcessorTag(raw_uid=tags[1], link="https://example.com"),
            ProcessorTag(raw_uid=tags[2], link="https://example.com", categories={TagCategory.network_domain}),
            ProcessorTag(raw_uid=tags[3], link="https://example.com", categories={TagCategory.feed_tag}),
            ProcessorTag(raw_uid=tags[4], link="https://example.com"),
        ]

        numbers_before = await count_total_tags_per_type()

        await apply_tags_to_entry(cataloged_entry.id, 1, processor_tags)

        numbers_after = await count_total_tags_per_type()

        assert numbers_after[TagPropertyType.link] == numbers_before.get(TagPropertyType.link, 0) + 4
        assert numbers_after[TagPropertyType.categories] == numbers_before.get(TagPropertyType.categories, 0) + 2
