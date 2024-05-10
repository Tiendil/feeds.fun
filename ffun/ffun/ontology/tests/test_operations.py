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
from ffun.ontology.operations import _save_tags, get_tags_for_entries


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
