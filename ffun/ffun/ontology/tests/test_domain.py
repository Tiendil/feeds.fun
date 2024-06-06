import uuid

import pytest

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.library.entities import Entry
from ffun.ontology import errors
from ffun.ontology.entities import ProcessorTag
from ffun.ontology.operations import (
    _get_relations_for_entry_and_tags,
    _register_relations_processors,
    _save_tags,
    apply_tags,
    apply_tags_properties,
    get_tags_properties,
    remove_relations_for_entries,
    tech_copy_relations,
)
from ffun.ontology.domain import apply_tags_to_entry, get_tags_ids_for_entries, get_ids_by_uids
from ffun.ontology.tests.helpers import assert_has_tags
from ffun.tags import converters


class TestApplyTagsToEntry:

    @pytest.mark.asyncio
    async def test_apply_no_tags(self, cataloged_entry: Entry, fake_processor_id: int):
        async with (TableSizeNotChanged("o_tags_properties"),
                    TableSizeNotChanged("o_relations"),
                    TableSizeNotChanged("o_relations_processors")):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, tags=[])

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {}

    @pytest.mark.asyncio
    async def test_apply_tags(self,
                              cataloged_entry: Entry,
                              fake_processor_id: int,
                              three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag]):

        three_processor_tags[1].link = "https://example.com"

        raw_to_uids = {tag.raw_uid: converters.normalize(tag.raw_uid) for tag in three_processor_tags}
        uids_to_ids = await get_ids_by_uids(raw_to_uids.values())

        async with (TableSizeDelta("o_tags_properties", delta=1),
                    TableSizeDelta("o_relations", delta=3),
                    TableSizeDelta("o_relations_processors", delta=3)):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, three_processor_tags)

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {cataloged_entry.id: set(uids_to_ids.values())}

    @pytest.mark.asyncio
    async def test_duplicated_tags(self,
                                   cataloged_entry: Entry,
                                   fake_processor_id: int,
                                   three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag]):

        three_processor_tags[0].raw_uid = three_processor_tags[0].raw_uid.lower()
        three_processor_tags[0].link = "https://example.com?x"

        three_processor_tags[1].link = "https://example.com?y"

        three_processor_tags[2].raw_uid = three_processor_tags[0].raw_uid.upper()
        three_processor_tags[2].link = "https://example.com?z"

        raw_to_uids = {tag.raw_uid: converters.normalize(tag.raw_uid) for tag in three_processor_tags}
        uids_to_ids = await get_ids_by_uids(raw_to_uids.values())

        async with (TableSizeDelta("o_tags_properties", delta=2),
                    TableSizeDelta("o_relations", delta=2),
                    TableSizeDelta("o_relations_processors", delta=2)):
            await apply_tags_to_entry(cataloged_entry.id, fake_processor_id, three_processor_tags)

        loaded_tags = await get_tags_ids_for_entries([cataloged_entry.id])

        assert loaded_tags == {cataloged_entry.id: {uids_to_ids[raw_to_uids[three_processor_tags[0].raw_uid]],
                                                    uids_to_ids[raw_to_uids[three_processor_tags[1].raw_uid]]}}
