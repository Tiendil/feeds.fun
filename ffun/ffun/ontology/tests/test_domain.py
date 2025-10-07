import copy

import pytest
from pytest_mock import MockerFixture

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId, TagId
from ffun.library.entities import Entry
from ffun.ontology import operations
from ffun.ontology.domain import (
    _inplace_filter_out_entry_tags,
    apply_tags_to_entry,
    copy_relations,
    get_ids_by_uids,
    get_tags_ids_for_entries,
    prepare_tags_for_entries,
    remove_orphaned_tags,
    remove_relations_for_tags,
)
from ffun.ontology.entities import NormalizedTag
from ffun.ontology.tests import helpers


class TestApplyTagsToEntry:

    @pytest.mark.asyncio
    async def test_apply_no_tags(self, cataloged_entry: Entry, fake_processor_id: int) -> None:
        async with (
            TableSizeNotChanged("o_tags_properties"),
            TableSizeNotChanged("o_relations"),
            TableSizeNotChanged("o_relations_processors"),
        ):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, tags=[])

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {}

    @pytest.mark.asyncio
    async def test_apply_tags(
        self,
        cataloged_entry: Entry,
        fake_processor_id: int,
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:

        three_processor_tags[1].link = "https://example.com"

        uids_to_ids = await get_ids_by_uids([tag.uid for tag in three_processor_tags])

        async with (
            TableSizeDelta("o_tags_properties", delta=3 + 1),
            TableSizeDelta("o_relations", delta=3),
            TableSizeDelta("o_relations_processors", delta=3),
        ):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, three_processor_tags)

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {cataloged_entry.id: set(uids_to_ids.values())}


def _no_type_inplace_filter_out_entry_tags(
    entry_tag_ids: dict[EntryId, set[int]], must_have_tags: set[int], min_tag_count: int
) -> set[int]:
    return _inplace_filter_out_entry_tags(  # type: ignore
        entry_tag_ids=entry_tag_ids,  # type: ignore
        must_have_tags=must_have_tags,  # type: ignore
        min_tag_count=min_tag_count,
    )


class TestInplaceFilterOutEntryTags:

    @pytest.mark.parametrize("min_tag_count", [0, 1, 10])
    @pytest.mark.parametrize("must_have_tags", [set(), {1}, {1, 2, 10}])
    @pytest.mark.asyncio
    async def test_no_entries(self, min_tag_count: int, must_have_tags: set[int]) -> None:
        entry_tag_ids: dict[EntryId, set[int]] = {}

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=entry_tag_ids, must_have_tags=must_have_tags, min_tag_count=min_tag_count
        )

        assert whole_tags == set()
        assert entry_tag_ids == {}

    @pytest.mark.parametrize("min_tag_count", [0, 1, 10])
    @pytest.mark.parametrize("must_have_tags", [set(), {1}, {1, 2, 10}])
    @pytest.mark.asyncio
    async def test_no_tags(self, min_tag_count: int, must_have_tags: set[int]) -> None:
        entry_ids = [new_entry_id(), new_entry_id()]

        entry_tag_ids: dict[EntryId, set[int]] = {
            entry_ids[0]: set(),
            entry_ids[1]: set(),
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=entry_tag_ids, must_have_tags=must_have_tags, min_tag_count=min_tag_count
        )

        assert whole_tags == set()
        assert entry_tag_ids == {
            entry_ids[0]: set(),
            entry_ids[1]: set(),
        }

    @pytest.mark.parametrize("must_have_tags", [set(), {100}, {100, 200}])
    @pytest.mark.asyncio
    async def test_filter_out_tags(self, must_have_tags: set[int]) -> None:
        entry_ids = [new_entry_id() for _ in range(5)]
        original_entry_tag_ids = {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        filtering_no = copy.deepcopy(original_entry_tag_ids)
        filtering_1 = copy.deepcopy(original_entry_tag_ids)
        filtering_2 = copy.deepcopy(original_entry_tag_ids)
        filtering_3 = copy.deepcopy(original_entry_tag_ids)
        filtering_10 = copy.deepcopy(original_entry_tag_ids)

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_no, must_have_tags=must_have_tags, min_tag_count=0
        )
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_1, must_have_tags=must_have_tags, min_tag_count=1
        )
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_2, must_have_tags=must_have_tags, min_tag_count=2
        )
        assert whole_tags == {2, 3, 4, 5}
        assert filtering_2 == {
            entry_ids[0]: {2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5},
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_3, must_have_tags=must_have_tags, min_tag_count=3
        )
        assert whole_tags == {3, 4}
        assert filtering_3 == {
            entry_ids[0]: {3, 4},
            entry_ids[1]: {3, 4},
            entry_ids[2]: {3, 4},
            entry_ids[3]: set(),
            entry_ids[4]: set(),
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_10, must_have_tags=must_have_tags, min_tag_count=10
        )
        assert whole_tags == set()
        assert filtering_10 == {
            entry_ids[0]: set(),
            entry_ids[1]: set(),
            entry_ids[2]: set(),
            entry_ids[3]: set(),
            entry_ids[4]: set(),
        }

    @pytest.mark.asyncio
    async def test_keep_must_have_tags(self) -> None:
        must_have_tags = {1, 4}

        entry_ids = [new_entry_id() for _ in range(5)]
        original_entry_tag_ids = {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        filtering_no = copy.deepcopy(original_entry_tag_ids)
        filtering_1 = copy.deepcopy(original_entry_tag_ids)
        filtering_2 = copy.deepcopy(original_entry_tag_ids)
        filtering_3 = copy.deepcopy(original_entry_tag_ids)
        filtering_10 = copy.deepcopy(original_entry_tag_ids)

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_no, must_have_tags=must_have_tags, min_tag_count=0
        )
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_1, must_have_tags=must_have_tags, min_tag_count=1
        )
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_2, must_have_tags=must_have_tags, min_tag_count=2
        )
        assert whole_tags == {1, 2, 3, 4, 5}
        assert filtering_2 == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5},
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_3, must_have_tags=must_have_tags, min_tag_count=3
        )
        assert whole_tags == {1, 3, 4}
        assert filtering_3 == {
            entry_ids[0]: {1, 3, 4},
            entry_ids[1]: {3, 4},
            entry_ids[2]: {3, 4},
            entry_ids[3]: set(),
            entry_ids[4]: set(),
        }

        whole_tags = _no_type_inplace_filter_out_entry_tags(
            entry_tag_ids=filtering_10, must_have_tags=must_have_tags, min_tag_count=10
        )
        assert whole_tags == {1, 4}
        assert filtering_10 == {
            entry_ids[0]: {1, 4},
            entry_ids[1]: {4},
            entry_ids[2]: {4},
            entry_ids[3]: set(),
            entry_ids[4]: set(),
        }


class TestPrepareTagsForEntries:

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        entry_tag_ids, tag_mapping = await prepare_tags_for_entries(
            entry_ids=[], must_have_tags=set(), min_tag_count=1
        )
        assert entry_tag_ids == {}
        assert tag_mapping == {}

    @pytest.mark.asyncio
    async def test_no_tags(self, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        entry_tag_ids, tag_mapping = await prepare_tags_for_entries(
            entry_ids=[cataloged_entry.id, another_cataloged_entry.id], must_have_tags=set(), min_tag_count=1
        )
        assert entry_tag_ids == {}
        assert tag_mapping == {}

    @pytest.mark.asyncio
    async def test_works(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        tags = five_processor_tags

        uids_to_ids = await get_ids_by_uids([tag.uid for tag in tags])

        tag_ids = [uids_to_ids[tag.uid] for tag in tags]

        await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, [tags[0], tags[1], tags[3], tags[4]])
        await apply_tags_to_entry(another_cataloged_entry.id, fake_processor_id, [tags[0], tags[2], tags[4]])

        entry_tag_ids, tag_mapping = await prepare_tags_for_entries(
            entry_ids=[cataloged_entry.id, another_cataloged_entry.id], must_have_tags=set(), min_tag_count=1
        )
        assert entry_tag_ids == {
            cataloged_entry.id: {tag_ids[0], tag_ids[1], tag_ids[3], tag_ids[4]},
            another_cataloged_entry.id: {tag_ids[0], tag_ids[2], tag_ids[4]},
        }
        assert tag_mapping == {tag_id: tag_uid for tag_uid, tag_id in uids_to_ids.items()}

    @pytest.mark.asyncio
    async def test_filtering_works(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        tags = five_processor_tags

        uids_to_ids = await get_ids_by_uids([tag.uid for tag in tags])

        tag_ids = [uids_to_ids[tag.uid] for tag in tags]

        await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, [tags[0], tags[1], tags[3], tags[4]])
        await apply_tags_to_entry(another_cataloged_entry.id, fake_processor_id, [tags[0], tags[2], tags[4]])

        entry_tag_ids, tag_mapping = await prepare_tags_for_entries(
            entry_ids=[cataloged_entry.id, another_cataloged_entry.id], must_have_tags={tag_ids[3]}, min_tag_count=2
        )
        assert entry_tag_ids == {
            cataloged_entry.id: {tag_ids[0], tag_ids[3], tag_ids[4]},
            another_cataloged_entry.id: {tag_ids[0], tag_ids[4]},
        }
        assert tag_mapping == {
            tag_ids[0]: tags[0].uid,
            tag_ids[3]: tags[3].uid,
            tag_ids[4]: tags[4].uid,
        }


class TestRemoveOrphanedTags:

    @pytest.mark.asyncio
    async def test_chunk(self, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:  # pylint: disable=W0613
        async with TableSizeDelta("o_tags", delta=-2):
            removed = await remove_orphaned_tags(chunk=2, protected_tags=[])

        assert removed == 2

    @pytest.mark.asyncio
    async def test_protected(self, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:  # pylint: disable=W0613
        removed = await remove_orphaned_tags(chunk=1000_000, protected_tags=[three_tags_ids[0], three_tags_ids[2]])

        assert removed > 0

        tags = await operations.get_tags_by_ids(list(three_tags_ids))

        assert set(tags.keys()) == {three_tags_ids[0], three_tags_ids[2]}

    @pytest.mark.asyncio
    async def test_foreign_key_violation(
        self,
        fake_processor_id: int,
        cataloged_entry: Entry,
        three_tags_ids: tuple[TagId, TagId, TagId],
        mocker: MockerFixture,
    ) -> None:

        await operations.apply_tags(execute, cataloged_entry.id, fake_processor_id, [three_tags_ids[0]])

        mocker.patch("ffun.ontology.operations.get_orphaned_tags", return_value=list(three_tags_ids))

        async with TableSizeNotChanged("o_tags"):
            async with TableSizeNotChanged("o_tags_properties"):
                assert await remove_orphaned_tags(chunk=1000_000, protected_tags=[]) == 0


class TestCopyRelations:

    @pytest.mark.asyncio
    async def test_nothing_to_copy(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        tags = five_processor_tags

        await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, [tags[0], tags[1], tags[2]])
        await apply_tags_to_entry(cataloged_entry.id, another_fake_processor_id, [tags[0], tags[2], tags[4]])

        await apply_tags_to_entry(another_cataloged_entry.id, fake_processor_id, [tags[2], tags[3], tags[4]])
        await apply_tags_to_entry(another_cataloged_entry.id, another_fake_processor_id, [tags[0], tags[4]])

        unexisting_tag_id = await helpers.unexisting_tag_id()

        async with TableSizeNotChanged("o_relations"):
            await copy_relations(
                processor_id=fake_processor_id, old_tag_id=unexisting_tag_id, new_tag_id=unexisting_tag_id + 1
            )

    @pytest.mark.asyncio
    async def test_copy(  # noqa: CFQ002
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        tags = five_processor_tags
        tag_ids = five_tags_ids

        await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, [tags[0], tags[2]])
        await apply_tags_to_entry(cataloged_entry.id, another_fake_processor_id, [tags[0], tags[2], tags[4]])

        await apply_tags_to_entry(another_cataloged_entry.id, fake_processor_id, [tags[2], tags[3], tags[4]])
        await apply_tags_to_entry(another_cataloged_entry.id, another_fake_processor_id, [tags[0], tags[4]])

        async with TableSizeDelta("o_relations", delta=2):
            async with TableSizeDelta("o_relations_processors", delta=2):
                await copy_relations(processor_id=fake_processor_id, old_tag_id=tag_ids[2], new_tag_id=tag_ids[1])

        relation_ids = await operations.get_relations_for(
            execute, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )
        signatures = await helpers.get_relation_signatures(relation_ids)

        expected_signatures = {
            (cataloged_entry.id, tag_ids[0], fake_processor_id),
            (cataloged_entry.id, tag_ids[0], another_fake_processor_id),
            (cataloged_entry.id, tag_ids[1], fake_processor_id),
            (cataloged_entry.id, tag_ids[2], fake_processor_id),
            (cataloged_entry.id, tag_ids[2], another_fake_processor_id),
            (cataloged_entry.id, tag_ids[4], another_fake_processor_id),
            (another_cataloged_entry.id, tag_ids[0], another_fake_processor_id),
            (another_cataloged_entry.id, tag_ids[1], fake_processor_id),
            (another_cataloged_entry.id, tag_ids[2], fake_processor_id),
            (another_cataloged_entry.id, tag_ids[3], fake_processor_id),
            (another_cataloged_entry.id, tag_ids[4], fake_processor_id),
            (another_cataloged_entry.id, tag_ids[4], another_fake_processor_id),
        }

        assert set(signatures) == expected_signatures

        # This copy will not create new relations (since they already created by previous operation),
        # but will bind new processor to existing relations
        async with TableSizeNotChanged("o_relations"):
            async with TableSizeDelta("o_relations_processors", delta=1):
                await copy_relations(
                    processor_id=another_fake_processor_id, old_tag_id=tag_ids[2], new_tag_id=tag_ids[1]
                )

        relation_ids = await operations.get_relations_for(
            execute, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )
        signatures = await helpers.get_relation_signatures(relation_ids)

        assert set(signatures) == expected_signatures | {
            (cataloged_entry.id, tag_ids[1], another_fake_processor_id),
        }


class TestRemoveRelationsForTags:

    @pytest.mark.asyncio
    async def test_no_tags(
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        tags = five_processor_tags

        await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, [tags[0], tags[1], tags[2]])
        await apply_tags_to_entry(cataloged_entry.id, another_fake_processor_id, [tags[0], tags[2], tags[4]])

        await apply_tags_to_entry(another_cataloged_entry.id, fake_processor_id, [tags[2], tags[3], tags[4]])
        await apply_tags_to_entry(another_cataloged_entry.id, another_fake_processor_id, [tags[0], tags[4]])

        async with TableSizeNotChanged("o_relations"):
            async with TableSizeNotChanged("o_relations_processors"):
                await remove_relations_for_tags(tag_ids=[])

    @pytest.mark.asyncio
    async def test_remove(  # noqa: CFQ002
        self,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
        fake_processor_id: int,
        another_fake_processor_id: int,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        tags = five_processor_tags
        tag_ids = five_tags_ids

        await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, [tags[0], tags[1], tags[2]])
        await apply_tags_to_entry(cataloged_entry.id, another_fake_processor_id, [tags[0], tags[2], tags[4]])

        await apply_tags_to_entry(another_cataloged_entry.id, fake_processor_id, [tags[2], tags[3], tags[4]])
        await apply_tags_to_entry(another_cataloged_entry.id, another_fake_processor_id, [tags[3], tags[4]])

        relations_to_remove = await operations.get_relations_for(execute, tag_ids=[tag_ids[1], tag_ids[3]])

        assert len(relations_to_remove) == 2

        # we remove 2 relations but 3 processors bindings
        async with TableSizeDelta("o_relations", delta=-2):
            async with TableSizeDelta("o_relations_processors", delta=-3):
                await remove_relations_for_tags(tag_ids=[tag_ids[1], tag_ids[3]])

        signatures = await helpers.get_relation_signatures(relations_to_remove)
        assert signatures == []
