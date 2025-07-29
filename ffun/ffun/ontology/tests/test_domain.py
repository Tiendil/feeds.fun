import pytest
import copy

from ffun.domain.domain import new_entry_id
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.library.entities import Entry
from ffun.ontology.domain import apply_tags_to_entry, get_ids_by_uids, get_tags_ids_for_entries, prepare_tags_for_entries, _inplace_filter_out_entry_tags
from ffun.ontology.entities import ProcessorTag
from ffun.tags import converters


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
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:

        three_processor_tags[1].link = "https://example.com"

        raw_to_uids = {tag.raw_uid: converters.normalize(tag.raw_uid) for tag in three_processor_tags}
        uids_to_ids = await get_ids_by_uids(raw_to_uids.values())

        async with (
            TableSizeDelta("o_tags_properties", delta=1),
            TableSizeDelta("o_relations", delta=3),
            TableSizeDelta("o_relations_processors", delta=3),
        ):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, three_processor_tags)

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {cataloged_entry.id: set(uids_to_ids.values())}

    @pytest.mark.asyncio
    async def test_duplicated_tags(
        self,
        cataloged_entry: Entry,
        fake_processor_id: int,
        three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag],
    ) -> None:

        three_processor_tags[0].raw_uid = three_processor_tags[0].raw_uid.lower()
        three_processor_tags[0].link = "https://example.com?x"

        three_processor_tags[1].link = "https://example.com?y"

        three_processor_tags[2].raw_uid = three_processor_tags[0].raw_uid.upper()
        three_processor_tags[2].link = "https://example.com?z"

        raw_to_uids = {tag.raw_uid: converters.normalize(tag.raw_uid) for tag in three_processor_tags}
        uids_to_ids = await get_ids_by_uids(raw_to_uids.values())

        async with (
            TableSizeDelta("o_tags_properties", delta=2),
            TableSizeDelta("o_relations", delta=2),
            TableSizeDelta("o_relations_processors", delta=2),
        ):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, three_processor_tags)

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {
            cataloged_entry.id: {
                uids_to_ids[raw_to_uids[three_processor_tags[0].raw_uid]],
                uids_to_ids[raw_to_uids[three_processor_tags[1].raw_uid]],
            }
        }


class TestInplaceFilterOutEntryTags:

    @pytest.mark.parametrize("min_tag_count", [0, 1, 10])
    @pytest.mark.parametrize("must_have_tags", [set(), {1}, {1, 2, 10}])
    @pytest.mark.asyncio
    async def test_no_entries(self, min_tag_count: int, must_have_tags: set[int]) -> None:
        entry_tag_ids = {}

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=entry_tag_ids,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=min_tag_count)

        assert whole_tags == set()
        assert entry_tag_ids == {}

    @pytest.mark.parametrize("min_tag_count", [0, 1, 10])
    @pytest.mark.parametrize("must_have_tags", [set(), {1}, {1, 2, 10}])
    @pytest.mark.asyncio
    async def test_no_tags(self, min_tag_count: int, must_have_tags: set[int]) -> None:
        entry_ids = [new_entry_id(), new_entry_id()]

        entry_tag_ids = {
            entry_ids[0]: set(),
            entry_ids[1]: set(),
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=entry_tag_ids,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=min_tag_count)

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

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_no,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=0)
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_1,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=1)
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_2,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=2)
        assert whole_tags == {2, 3, 4, 5}
        assert filtering_2 == {
            entry_ids[0]: {2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5},
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_3,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=3)
        assert whole_tags == {3, 4}
        assert filtering_3 == {
            entry_ids[0]: {3, 4},
            entry_ids[1]: {3, 4},
            entry_ids[2]: {3, 4},
            entry_ids[3]: set(),
            entry_ids[4]: set(),
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_10,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=10)
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

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_no,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=0)
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_1,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=1)
        assert whole_tags == {1, 2, 3, 4, 5, 6}
        assert filtering_no == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5, 6},
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_2,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=2)
        assert whole_tags == {1, 2, 3, 4, 5}
        assert filtering_2 == {
            entry_ids[0]: {1, 2, 3, 4},
            entry_ids[1]: {2, 3, 4},
            entry_ids[2]: {3, 4, 5},
            entry_ids[3]: set(),
            entry_ids[4]: {5},
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_3,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=3)
        assert whole_tags == {1, 3, 4}
        assert filtering_3 == {
            entry_ids[0]: {1, 3, 4},
            entry_ids[1]: {3, 4},
            entry_ids[2]: {3, 4},
            entry_ids[3]: set(),
            entry_ids[4]: set(),
        }

        whole_tags = _inplace_filter_out_entry_tags(entry_tag_ids=filtering_10,
                                                    must_have_tags=must_have_tags,
                                                    min_tag_count=10)
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
    async def test(self) -> None:
        pass
