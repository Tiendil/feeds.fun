import datetime
import uuid
from itertools import chain

import pytest
import pytest_asyncio
from ffun.core import utils
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_times_is_near
from ffun.feeds import domain as f_domain
from ffun.feeds.tests import make as f_make
from ffun.library.domain import get_entry
from ffun.library.entities import Entry
from ffun.ontology.operations import (_get_relations_for_entry_and_tags, _register_relations_processors, _save_tags,
                                      get_tags_for_entries)


class TestSaveTags:

    @pytest.mark.asyncio
    async def test_no_tags(self, cataloged_entry: Entry) -> None:
        async with TableSizeNotChanged("o_relations"):
            await _save_tags(execute, cataloged_entry.id, [])

    @pytest.mark.asyncio
    async def test(self,
                   cataloged_entry: Entry,
                   another_cataloged_entry: Entry,
                   three_tags_ids: tuple[int, int, int]) -> None:

        async with TableSizeDelta("o_relations", delta=4):
            await _save_tags(execute, cataloged_entry.id, three_tags_ids[:2])
            await _save_tags(execute, another_cataloged_entry.id, three_tags_ids[1:])

        tags = await get_tags_for_entries(execute, [cataloged_entry.id, another_cataloged_entry.id])

        assert tags == {
            cataloged_entry.id: {three_tags_ids[0], three_tags_ids[1]},
            another_cataloged_entry.id: {three_tags_ids[1], three_tags_ids[2]},
        }


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
            await _register_relations_processors(execute,
                                                 relations_ids=list(relations.values()),
                                                 processor_id=fake_processor_id)

        sql = "SELECT relation_id, processor_id FROM o_relations_processors WHERE relation_id = ANY(%(relations_ids)s)"

        result = await execute(sql, {"relations_ids": list(relations.values())})

        assert {row["relation_id"]: fake_processor_id for row in result} == {relation_id: fake_processor_id for relation_id in relations.values()}

    @pytest.mark.asyncio
    async def test_duplicated(self, cataloged_entry: Entry, fake_processor_id: int, three_tags_ids: tuple[int, int, int]) -> None:
        await _save_tags(execute, cataloged_entry.id, three_tags_ids)

        relations = await _get_relations_for_entry_and_tags(execute, cataloged_entry.id, three_tags_ids)

        relation_ids = list(relations.values())

        async with TableSizeDelta("o_relations_processors", delta=3):
            await _register_relations_processors(execute,
                                                 relations_ids=relation_ids[:2],
                                                 processor_id=fake_processor_id)
            await _register_relations_processors(execute,
                                                 relations_ids=relation_ids[1:],
                                                 processor_id=fake_processor_id)

        sql = "SELECT relation_id, processor_id FROM o_relations_processors WHERE relation_id = ANY(%(relations_ids)s)"

        result = await execute(sql, {"relations_ids": list(relations.values())})

        assert {row["relation_id"]: fake_processor_id for row in result} == {relation_id: fake_processor_id for relation_id in relations.values()}


class TestGetRelationsForEntryAndTags:
    "Tested in other tests & code."
