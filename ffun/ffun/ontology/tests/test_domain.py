import pytest

from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.library.entities import Entry
from ffun.ontology.domain import apply_tags_to_entry, get_ids_by_uids, get_tags_ids_for_entries
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
