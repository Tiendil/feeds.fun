import uuid
import zoneinfo
from itertools import chain

import pytest
from ffun.core import utils
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_times_is_near
from ffun.feeds import domain as f_domain
from ffun.feeds.tests import make as f_make
from ffun.library.domain import get_entry
from ffun.library.entities import Entry
from ffun.library.operations import (all_entries_iterator, catalog_entries, check_stored_entries_by_external_ids,
                                     get_entries_by_ids, update_external_url)
from ffun.library.tests import make


class TestCatalogEntries:

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        async with TableSizeNotChanged("l_entries"):
            await catalog_entries([])

    @pytest.mark.asyncio
    async def test_success(self, new_entry: Entry, another_new_entry: Entry) -> None:

        entries_data = [new_entry, another_new_entry]

        async with TableSizeDelta("l_entries", delta=2):
            await catalog_entries(entries_data)

        loaded_entries = await get_entries_by_ids(ids=[new_entry.id, another_new_entry.id])

        loaded_new_entry = loaded_entries[new_entry.id]
        loaded_another_new_entry = loaded_entries[another_new_entry.id]

        assert len(loaded_entries) == 2

        assert loaded_new_entry is not None
        assert loaded_another_new_entry is not None

        assert_times_is_near(loaded_new_entry.cataloged_at, utils.now())
        assert_times_is_near(loaded_another_new_entry.cataloged_at, utils.now())

        assert loaded_new_entry == new_entry.replace(cataloged_at=loaded_new_entry.cataloged_at)
        assert loaded_another_new_entry == another_new_entry.replace(
            cataloged_at=loaded_another_new_entry.cataloged_at
        )


class TestCheckStoredEntriesByExternalIds:

    @pytest.mark.asyncio
    async def test_no_entries_stored(self, loaded_feed_id: uuid.UUID) -> None:
        entries = [make.fake_entry(loaded_feed_id) for _ in range(3)]
        external_ids = [entry.external_id for entry in entries]

        stored_entries = await check_stored_entries_by_external_ids(loaded_feed_id, external_ids)

        assert stored_entries == set()

    @pytest.mark.asyncio
    async def test_all_entries_stored(self, loaded_feed_id: uuid.UUID) -> None:
        entries = await make.n_entries(loaded_feed_id, n=3)
        external_ids = {entry.external_id for entry in entries.values()}

        stored_entries = await check_stored_entries_by_external_ids(loaded_feed_id, list(external_ids))

        assert stored_entries == external_ids

    @pytest.mark.asyncio
    async def test_some_entries_stored(self, loaded_feed_id: uuid.UUID) -> None:
        new_entries = [make.fake_entry(loaded_feed_id) for _ in range(3)]
        saved_entries = await make.n_entries(loaded_feed_id, n=2)
        external_ids = [entry.external_id for entry in new_entries] + [entry.external_id for entry in saved_entries.values()]

        stored_entries = await check_stored_entries_by_external_ids(loaded_feed_id, external_ids)

        assert stored_entries == set(entry.external_id for entry in saved_entries.values())


class TestGetEntriesByIds:

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        entries = await get_entries_by_ids(ids=[])
        assert entries == {}

    @pytest.mark.asyncio
    async def test_success(self, loaded_feed_id: uuid.UUID, another_loaded_feed_id: uuid.UUID) -> None:
        entries = await make.n_entries(loaded_feed_id, n=3)
        another_entries = await make.n_entries(another_loaded_feed_id, n=3)

        entries_list = list(entries.values())
        another_entries_list = list(another_entries.values())

        entries_to_load = [*entries_list[:2], *another_entries_list[:2]]

        loaded_entries = await get_entries_by_ids(ids=[entry.id for entry in entries_to_load])

        assert len(loaded_entries) == 4
        assert entries_to_load[0] == loaded_entries[entries_to_load[0].id]
        assert entries_to_load[1] == loaded_entries[entries_to_load[1].id]
        assert another_entries_list[0] == loaded_entries[another_entries_list[0].id]
        assert another_entries_list[1] == loaded_entries[another_entries_list[1].id]


class TestAllEntriesIterator:
    @pytest.mark.parametrize("chunk", [1, 2, 3, 4, 5, 6, 7])
    @pytest.mark.asyncio
    async def test(self, chunk: int) -> None:
        feed_1_data = f_make.fake_feed()
        feed_1_id = await f_domain.save_feed(feed_1_data)

        feed_2_data = f_make.fake_feed()
        feed_2_id = await f_domain.save_feed(feed_2_data)

        entries_1_data = [make.fake_entry(feed_1_id) for _ in range(3)]
        entries_2_data = [make.fake_entry(feed_2_id) for _ in range(3)]

        await catalog_entries(entries_1_data)
        await catalog_entries(entries_2_data)

        ids = [(e.feed_id, e.id) for e in chain(entries_1_data, entries_2_data)]

        ids.sort()

        found_ids = [
            (entry.feed_id, entry.id)
            async for entry in all_entries_iterator(chunk=chunk)
            if (entry.feed_id, entry.id) in ids
        ]

        assert found_ids == ids


class TestUpdateExternalUrl:
    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        new_url = make.fake_url()

        assert cataloged_entry.external_url != new_url

        await update_external_url(cataloged_entry.id, new_url)

        loaded_entry = await get_entry(cataloged_entry.id)
        assert loaded_entry.external_url == new_url

        loaded_another_entry = await get_entry(another_cataloged_entry.id)
        assert loaded_another_entry.external_url == another_cataloged_entry.external_url
