import uuid

import pytest

from ffun.core import utils
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import Delta, TableSizeDelta, TableSizeNotChanged
from ffun.domain.entities import EntryId, TagId, TagUid
from ffun.feeds.entities import Feed
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make
from ffun.ontology import errors
from ffun.ontology.domain import apply_tags_to_entry
from ffun.ontology.entities import NormalizedTag, TagProperty, TagPropertyType
from ffun.ontology.operations import (
    _save_tags,
    apply_tags,
    apply_tags_properties,
    copy_relations_to_new_tag,
    copy_tag_properties,
    count_new_tags_at,
    count_total_tags,
    count_total_tags_per_category,
    count_total_tags_per_type,
    get_or_create_id_by_tag,
    get_orphaned_tags,
    get_relations_for,
    get_tags_by_ids,
    get_tags_properties,
    register_relations_processors,
    register_tag,
    remove_relations,
    remove_tags,
    tag_frequency_statistics,
)
from ffun.ontology.tests.helpers import assert_has_tags, get_relation_signatures
from ffun.tags.entities import TagCategory


async def assert_tags_processors(entry_id: EntryId, tag_processors: dict[TagId, set[int]]) -> None:
    expected_relations = set()

    for tag_id, processor_ids in tag_processors.items():
        for processor_id in processor_ids:
            relation_ids = await get_relations_for(
                execute, entry_ids=[entry_id], tag_ids=[tag_id], processor_ids=[processor_id]
            )
            assert len(relation_ids) == 1

            expected_relations.update(relation_ids)

    all_relations = await get_relations_for(execute, entry_ids=[entry_id])

    assert set(all_relations) == expected_relations


class TestSaveTags:
    @pytest.mark.asyncio
    async def test_no_tags(self, cataloged_entry: Entry) -> None:
        async with TableSizeNotChanged("o_relations"):
            await _save_tags(execute, cataloged_entry.id, [])

    @pytest.mark.asyncio
    async def test(
        self, cataloged_entry: Entry, another_cataloged_entry: Entry, three_tags_ids: tuple[TagId, TagId, TagId]
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
            await register_relations_processors(execute, [], fake_processor_id)

    @pytest.mark.asyncio
    async def test(
        self, cataloged_entry: Entry, fake_processor_id: int, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        await _save_tags(execute, cataloged_entry.id, three_tags_ids[:2])

        relations_ids = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id], tag_ids=list(three_tags_ids[:2])
        )

        async with TableSizeDelta("o_relations_processors", delta=2):
            await register_relations_processors(execute, relations_ids=relations_ids, processor_id=fake_processor_id)

        await assert_tags_processors(
            entry_id=cataloged_entry.id,
            tag_processors={three_tags_ids[0]: {fake_processor_id}, three_tags_ids[1]: {fake_processor_id}},
        )

    @pytest.mark.asyncio
    async def test_duplicated(
        self, cataloged_entry: Entry, fake_processor_id: int, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        await _save_tags(execute, cataloged_entry.id, three_tags_ids)

        relation_ids = await get_relations_for(execute, entry_ids=[cataloged_entry.id], tag_ids=list(three_tags_ids))

        async with TableSizeDelta("o_relations_processors", delta=3):
            await register_relations_processors(
                execute, relations_ids=relation_ids[:2], processor_id=fake_processor_id
            )
            await register_relations_processors(
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


class TestRemoveRelations:
    @pytest.mark.asyncio
    async def test_nothing_to_remove(
        self, cataloged_entry: Entry, another_cataloged_entry: Entry  # pylint: disable=W0613
    ) -> None:  # pylint: disable=W0613
        async with TableSizeNotChanged("o_relations"):
            await remove_relations(execute, [])

    @pytest.mark.asyncio
    async def test_success(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:
        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=list(three_tags_ids[:2])
            )

        async with transaction() as trx:
            await apply_tags(
                trx,
                entry_id=cataloged_entry.id,
                processor_id=another_fake_processor_id,
                tag_ids=list(three_tags_ids[1:]),
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=another_cataloged_entry.id, processor_id=fake_processor_id, tag_ids=list(three_tags_ids)
            )

        async with transaction() as trx:
            await apply_tags(
                trx,
                entry_id=another_cataloged_entry.id,
                processor_id=another_fake_processor_id,
                tag_ids=list(three_tags_ids),
            )

        async with (
            TableSizeDelta("o_relations_processors", delta=-4),
            TableSizeDelta("o_relations", delta=-3),
            TableSizeNotChanged("o_tags"),
        ):
            async with transaction() as trx:
                relation_ids = await get_relations_for(trx, entry_ids=[cataloged_entry.id])
                await remove_relations(trx, relation_ids)

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
        three_tags_by_uids: dict[TagUid, TagId],
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
        fake_processor_id: int,
    ) -> None:

        properties = []

        for tag in three_processor_tags:
            tag.link = f"https://example.com?{tag.uid}"
            properties.extend(
                tag.build_properties_for(tag_id=three_tags_by_uids[tag.uid], processor_id=fake_processor_id)
            )

        async with TableSizeDelta("o_tags_properties", delta=3 + 3):
            await apply_tags_properties(execute, properties)

        loaded_tags_properties = await get_tags_properties(three_tags_by_uids.values())

        loaded_tags_properties.sort(key=lambda x: x.tag_id)
        properties.sort(key=lambda x: x.tag_id)

        assert loaded_tags_properties == properties

    @pytest.mark.asyncio
    async def test_save_duplicated(
        self,
        three_tags_by_uids: dict[TagUid, TagId],
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
        fake_processor_id: int,
    ) -> None:

        properties = []

        for tag in three_processor_tags:
            tag.link = f"https://example.com?{tag.uid}"
            properties.extend(
                [
                    p
                    for p in tag.build_properties_for(
                        tag_id=three_tags_by_uids[tag.uid], processor_id=fake_processor_id
                    )
                    if p.type == TagPropertyType.link
                ]
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
        three_tags_by_uids: dict[TagUid, TagId],
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
        fake_processor_id: int,
    ) -> None:

        properties = []

        for tag in three_processor_tags:
            tag.link = f"https://example.com?{tag.uid}"
            properties.extend(
                tag.build_properties_for(tag_id=three_tags_by_uids[tag.uid], processor_id=fake_processor_id)
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
                await get_or_create_id_by_tag(uuid.uuid4().hex)  # type: ignore


class TestCountTotalTagsPerCategory:

    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry) -> None:
        tags = [TagUid(uuid.uuid4().hex) for _ in range(5)]

        processor_tags = [
            NormalizedTag(uid=tags[0], link=None, categories={TagCategory.test_raw}),
            NormalizedTag(uid=tags[1], link=None, categories={TagCategory.network_domain}),
            NormalizedTag(uid=tags[2], link=None, categories={TagCategory.feed_tag}),
            NormalizedTag(uid=tags[3], link=None, categories={TagCategory.network_domain, TagCategory.feed_tag}),
            NormalizedTag(uid=tags[4], link=None, categories={TagCategory.feed_tag}),
        ]

        numbers_before = await count_total_tags_per_category()

        await apply_tags_to_entry(cataloged_entry.id, 1, processor_tags)

        numbers_after = await count_total_tags_per_category()

        assert numbers_after[TagCategory.network_domain] == numbers_before[TagCategory.network_domain] + 2
        assert numbers_after[TagCategory.feed_tag] == numbers_before[TagCategory.feed_tag] + 3


class TestCountTotalTagsPerType:

    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry) -> None:
        tags = [TagUid(uuid.uuid4().hex) for _ in range(5)]

        processor_tags = [
            NormalizedTag(uid=tags[0], link=None, categories={TagCategory.test_raw}),
            NormalizedTag(uid=tags[1], link="https://example.com", categories={TagCategory.test_raw}),
            NormalizedTag(uid=tags[2], link="https://example.com", categories={TagCategory.network_domain}),
            NormalizedTag(uid=tags[3], link="https://example.com", categories={TagCategory.feed_tag}),
            NormalizedTag(uid=tags[4], link="https://example.com", categories={TagCategory.test_raw}),
        ]

        numbers_before = await count_total_tags_per_type()

        await apply_tags_to_entry(cataloged_entry.id, 1, processor_tags)

        numbers_after = await count_total_tags_per_type()

        assert numbers_after[TagPropertyType.link] == numbers_before.get(TagPropertyType.link, 0) + 4
        assert numbers_after[TagPropertyType.categories] == numbers_before.get(TagPropertyType.categories, 0) + 5


class TestCountNewTagsAt:

    @pytest.mark.asyncio
    async def test(self) -> None:
        count_before = await count_new_tags_at(utils.now().date())

        for _ in range(3):
            await register_tag(TagUid(uuid.uuid4().hex))

        count_after = await count_new_tags_at(utils.now().date())

        assert count_after == count_before + 3


class TestGetTagsForEntries:
    """Tested in other tests & code."""


class TestTagFrequencyStatistics:

    @pytest.mark.asyncio
    async def test(
        self, saved_feed: Feed, fake_processor_id: int, five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId]
    ) -> None:
        buckets = [1, 2, 3, 5, 7]
        tags = five_tags_ids

        stats_before = await tag_frequency_statistics(buckets)

        entries = await l_make.n_entries_list(saved_feed, 8)

        for entry in entries[:3]:
            await apply_tags(execute, entry.id, fake_processor_id, [tags[0]])

        for entry in entries[:5]:
            await apply_tags(execute, entry.id, fake_processor_id, [tags[1], tags[2]])

        for entry in entries:
            await apply_tags(execute, entry.id, fake_processor_id, [tags[3]])

        stats_after = await tag_frequency_statistics(buckets)

        assert len(stats_before) == len(buckets) == len(stats_after)

        assert stats_before[0] == stats_after[0]
        assert stats_before[1] == stats_after[1]
        assert stats_before[2].replace(count=stats_before[2].count + 1) == stats_after[2]
        assert stats_before[3].replace(count=stats_before[3].count + 2) == stats_after[3]
        assert stats_before[4].replace(count=stats_before[4].count + 1) == stats_after[4]


class TestGetOrphanedTags:

    @pytest.mark.asyncio
    async def test_no_some_orphans(
        self, fake_processor_id: int, cataloged_entry: Entry, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        await apply_tags(
            execute, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[three_tags_ids[1]]
        )

        orphans = await get_orphaned_tags(execute, limit=1000_000, protected_tags=[])

        assert three_tags_ids[0] in orphans
        assert three_tags_ids[1] not in orphans
        assert three_tags_ids[2] in orphans

    @pytest.mark.asyncio
    async def test_limit(self, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:  # pylint: disable=W0613
        all_orphans = await get_orphaned_tags(execute, limit=1000_000, protected_tags=[])

        assert len(all_orphans) > 2

        orphans = await get_orphaned_tags(execute, limit=2, protected_tags=[])

        assert len(orphans) == 2

        assert orphans[0] in all_orphans
        assert orphans[1] in all_orphans

    @pytest.mark.asyncio
    async def test_protected(self, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:  # pylint: disable=W0613
        orphans = await get_orphaned_tags(
            execute, limit=1000_000, protected_tags=[three_tags_ids[0], three_tags_ids[2]]
        )

        assert three_tags_ids[0] not in orphans
        assert three_tags_ids[1] in orphans
        assert three_tags_ids[2] not in orphans


class TestRemoveTags:

    @pytest.mark.asyncio
    async def test_no_tags(self, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:  # pylint: disable=W0613
        async with TableSizeNotChanged("o_tags"):
            await remove_tags(execute, [])

    @pytest.mark.asyncio
    async def test_some_tags(
        self,
        fake_processor_id: int,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:

        properties = []

        for tag_id, tag in zip(five_tags_ids[2:], five_processor_tags[2:]):
            tag.link = f"https://example.com?{tag.uid}"
            properties.append(tag.build_properties_for(tag_id=tag_id, processor_id=fake_processor_id)[0])

        await apply_tags_properties(execute, properties)

        async with TableSizeDelta("o_tags", delta=-3):
            async with TableSizeDelta("o_tags_properties", delta=-2):
                assert await remove_tags(execute, [five_tags_ids[0], five_tags_ids[2], five_tags_ids[4]])

        tags = await get_tags_by_ids(list(five_tags_ids))

        assert set(tags.keys()) == {five_tags_ids[1], five_tags_ids[3]}

        saved_properties = await get_tags_properties(list(five_tags_ids))
        assert {property.tag_id for property in saved_properties} == {five_tags_ids[3]}

    @pytest.mark.asyncio
    async def test_foreign_key_violation(
        self,
        fake_processor_id: int,
        cataloged_entry: Entry,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:

        await apply_tags(execute, cataloged_entry.id, fake_processor_id, [three_tags_ids[0]])

        async with TableSizeNotChanged("o_tags"):
            async with TableSizeNotChanged("o_tags_properties"):
                assert not await remove_tags(execute, list(three_tags_ids))


class TestGetRelationsFor:
    @pytest.mark.asyncio
    async def test_no_filters(self, cataloged_entry: Entry) -> None:  # pylint: disable=W0613
        with pytest.raises(errors.AtLeastOneFilterMustBeDefined):
            await get_relations_for(execute)

    @pytest.mark.asyncio
    async def test_no_results_guarantied(self, cataloged_entry: Entry) -> None:  # pylint: disable=W0613
        assert await get_relations_for(execute, entry_ids=[], tag_ids=[], processor_ids=[]) == []
        assert await get_relations_for(execute, entry_ids=[]) == []
        assert await get_relations_for(execute, tag_ids=[]) == []
        assert await get_relations_for(execute, processor_ids=[]) == []

    @pytest.mark.asyncio
    async def test_no_relations_for_entries(
        self, cataloged_entry: Entry, another_cataloged_entry: Entry  # pylint: disable=W0613
    ) -> None:  # pylint: disable=W0613
        relation_ids = await get_relations_for(execute, entry_ids=[cataloged_entry.id, another_cataloged_entry.id])
        assert relation_ids == []

    @pytest.mark.asyncio
    async def test_no_relations_for_tags(
        self, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:  # pylint: disable=W0613
        relation_ids = await get_relations_for(execute, tag_ids=list(three_tags_ids))
        assert relation_ids == []

    @pytest.mark.asyncio
    async def test_some_entries(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:
        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[three_tags_ids[0]]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tag_ids=[three_tags_ids[2]]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=another_cataloged_entry.id, processor_id=fake_processor_id, tag_ids=list(three_tags_ids)
            )

        relation_1_ids = await get_relations_for(execute, entry_ids=[cataloged_entry.id])
        expected_relation_1_ids = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id], tag_ids=list(three_tags_ids)
        )
        assert len(relation_1_ids) == 2
        assert set(relation_1_ids) == set(expected_relation_1_ids)

        relation_2_ids = await get_relations_for(execute, entry_ids=[another_cataloged_entry.id])
        expected_relation_2_ids = await get_relations_for(
            execute, entry_ids=[another_cataloged_entry.id], tag_ids=list(three_tags_ids)
        )
        assert len(relation_2_ids) == 3
        assert set(relation_2_ids) == set(expected_relation_2_ids)

        relation_3_ids = await get_relations_for(execute, entry_ids=[cataloged_entry.id, another_cataloged_entry.id])
        assert len(relation_3_ids) == 5
        assert set(relation_3_ids) == set(relation_1_ids) | set(relation_2_ids)

    @pytest.mark.asyncio
    async def test_some_tags(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:
        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[three_tags_ids[0]]
            )

        async with transaction() as trx:
            await apply_tags(
                trx, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tag_ids=[three_tags_ids[2]]
            )

        async with transaction() as trx:
            await apply_tags(
                trx,
                entry_id=another_cataloged_entry.id,
                processor_id=fake_processor_id,
                tag_ids=list(three_tags_ids[1:]),
            )

        relation_1_ids = await get_relations_for(execute, tag_ids=[three_tags_ids[0]])
        expected_relation_1_ids = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id], tag_ids=[three_tags_ids[0]]
        )
        assert len(relation_1_ids) == 1
        assert set(relation_1_ids) == set(expected_relation_1_ids)

        relation_2_ids = await get_relations_for(execute, tag_ids=[three_tags_ids[2]])
        expected_relation_2_ids_1 = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id], tag_ids=[three_tags_ids[2]]
        )
        expected_relation_2_ids_2 = await get_relations_for(
            execute, entry_ids=[another_cataloged_entry.id], tag_ids=[three_tags_ids[2]]
        )
        assert len(relation_2_ids) == 2
        assert set(relation_2_ids) == set(expected_relation_2_ids_1) | set(expected_relation_2_ids_2)

        relation_3_ids = await get_relations_for(execute, tag_ids=[three_tags_ids[0], three_tags_ids[2]])
        assert len(relation_3_ids) == 3
        assert set(relation_3_ids) == set(relation_1_ids) | set(relation_2_ids)

    @pytest.mark.asyncio
    async def test_some_processors(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:
        await apply_tags(
            execute, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[three_tags_ids[0]]
        )

        await apply_tags(
            execute, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tag_ids=[three_tags_ids[2]]
        )

        await apply_tags(
            execute,
            entry_id=another_cataloged_entry.id,
            processor_id=fake_processor_id,
            tag_ids=list(three_tags_ids[1:]),
        )

        relation_1_ids = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id, another_cataloged_entry.id], processor_ids=[fake_processor_id]
        )
        expected_relation_1_ids_1 = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id], tag_ids=[three_tags_ids[0]]
        )
        expected_relation_1_ids_2 = await get_relations_for(
            execute, entry_ids=[another_cataloged_entry.id], tag_ids=[three_tags_ids[1], three_tags_ids[2]]
        )
        assert len(relation_1_ids) == 3
        assert set(relation_1_ids) == set(expected_relation_1_ids_1) | set(expected_relation_1_ids_2)

        relation_2_ids = await get_relations_for(
            execute,
            entry_ids=[cataloged_entry.id, another_cataloged_entry.id],
            processor_ids=[another_fake_processor_id],
        )
        expected_relation_2_ids = await get_relations_for(
            execute, entry_ids=[cataloged_entry.id], tag_ids=[three_tags_ids[2]]
        )
        assert len(relation_2_ids) == 1
        assert set(relation_2_ids) == set(expected_relation_2_ids)

        relation_3_ids = await get_relations_for(
            execute,
            entry_ids=[cataloged_entry.id, another_cataloged_entry.id],
            processor_ids=[fake_processor_id, another_fake_processor_id],
        )
        assert len(relation_3_ids) == 4
        assert set(relation_3_ids) == set(relation_1_ids) | set(relation_2_ids)


class TestCopyRelationsToNewTag:

    @pytest.mark.asyncio
    async def test_no_relations(self, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:
        async with TableSizeNotChanged("o_relations"):
            new_relation_ids = await copy_relations_to_new_tag(execute, [], three_tags_ids[0])
            assert new_relation_ids == []

    @pytest.mark.asyncio
    async def test_create_new(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
    ) -> None:
        tags = five_tags_ids

        await apply_tags(execute, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[tags[0]])

        await apply_tags(
            execute, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tag_ids=[tags[2]]
        )

        await apply_tags(
            execute,
            entry_id=another_cataloged_entry.id,
            processor_id=fake_processor_id,
            tag_ids=[tags[1], tags[2], tags[3]],
        )

        assert await get_relations_for(execute, tag_ids=[tags[4]]) == []

        relation_ids = await get_relations_for(execute, tag_ids=[tags[2]])

        async with TableSizeDelta("o_relations", delta=2):
            new_relation_ids = await copy_relations_to_new_tag(execute, relation_ids, tags[4])

        assert len(new_relation_ids) == 2

        signatures = await get_relation_signatures(new_relation_ids)

        # this method do not copy processors
        assert set(signatures) == {
            (cataloged_entry.id, tags[4], None),
            (another_cataloged_entry.id, tags[4], None),
        }

    @pytest.mark.asyncio
    async def test_partial_rewrite(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
    ) -> None:
        tags = five_tags_ids

        await apply_tags(execute, entry_id=cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[tags[0]])

        await apply_tags(
            execute, entry_id=cataloged_entry.id, processor_id=another_fake_processor_id, tag_ids=[tags[2]]
        )

        await apply_tags(
            execute, entry_id=another_cataloged_entry.id, processor_id=fake_processor_id, tag_ids=[tags[1], tags[3]]
        )

        relation_ids = await get_relations_for(execute, tag_ids=[tags[0], tags[3]])

        # relation between cataloged_entry and tags[2] already exists => delta=1
        async with TableSizeDelta("o_relations", delta=1):
            new_relation_ids = await copy_relations_to_new_tag(execute, relation_ids, tags[2])

        assert len(new_relation_ids) == 2

        signatures = await get_relation_signatures(new_relation_ids)

        # this method do not copy processors
        assert set(signatures) == {
            (cataloged_entry.id, tags[2], another_fake_processor_id),
            (another_cataloged_entry.id, tags[2], None),
        }


class TestCopyTagProperties:

    @pytest.mark.asyncio
    async def test(
        self,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:
        tag_ids = three_tags_ids

        properties = [
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.categories,
                value=TagCategory.test_raw.name,
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.link,
                value="https://example.com",
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.categories,
                value=TagCategory.test_final.name,
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[1],
                type=TagPropertyType.categories,
                value=TagCategory.test_preserve.name,
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[1],
                type=TagPropertyType.link,
                value="https://example.org",
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[2],
                type=TagPropertyType.categories,
                value=TagCategory.test_raw.name,
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
        ]

        await apply_tags_properties(execute, properties)

        async with TableSizeDelta("o_tags_properties", delta=2):
            await copy_tag_properties(
                execute, processor_id=fake_processor_id, old_tag_id=tag_ids[0], new_tag_id=tag_ids[2]
            )

        saved_properties = await get_tags_properties([tag_ids[2]])

        saved_properties_1 = [property for property in saved_properties if property.processor_id == fake_processor_id]
        saved_properties_2 = [
            property for property in saved_properties if property.processor_id == another_fake_processor_id
        ]

        saved_properties_1.sort(key=lambda x: (x.type, x.value))

        assert len(saved_properties_1) == 2
        assert len(saved_properties_2) == 1

        assert saved_properties_1[0] == properties[1].replace(tag_id=tag_ids[2])
        assert saved_properties_1[1] == properties[0].replace(tag_id=tag_ids[2])

        assert saved_properties_2[0] == properties[-1].replace(tag_id=tag_ids[2])

    @pytest.mark.asyncio
    async def test_rewrite(
        self,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
    ) -> None:
        tag_ids = three_tags_ids

        properties = [
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.categories,
                value=TagCategory.test_raw.name,
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.link,
                value="https://example.com",
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.categories,
                value=TagCategory.test_final.name,
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[1],
                type=TagPropertyType.categories,
                value=TagCategory.test_preserve.name,
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[1],
                type=TagPropertyType.link,
                value="https://example.org",
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[2],
                type=TagPropertyType.link,
                value="https://example.com",
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
        ]

        await apply_tags_properties(execute, properties)

        async with TableSizeDelta("o_tags_properties", delta=1):
            await copy_tag_properties(
                execute, processor_id=fake_processor_id, old_tag_id=tag_ids[0], new_tag_id=tag_ids[2]
            )

        saved_properties = await get_tags_properties([tag_ids[2]])
        saved_properties = [property for property in saved_properties if property.type == TagPropertyType.categories]

        assert len(saved_properties) == 1

        assert saved_properties[0] == properties[0].replace(tag_id=tag_ids[2])
