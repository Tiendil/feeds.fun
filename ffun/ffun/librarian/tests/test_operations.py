import pytest

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import ProcessorId
from ffun.feeds.entities import Feed
from ffun.librarian import operations
from ffun.librarian.tests import helpers
from ffun.library.tests import make as l_make


class TestAddEntriesToFailedStorage:
    @pytest.mark.asyncio
    async def test_add_entries(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        entries = await l_make.n_entries(loaded_feed, n=13)

        entries_to_add = list(entries)[:5]

        async with TableSizeDelta("ln_failed_entries", delta=5):
            await operations.add_entries_to_failed_storage(fake_processor_id, entries_to_add)

        failed_entries = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)

        assert set(entries_to_add) <= set(failed_entries)


class TestGetFailedEntries:
    @pytest.mark.asyncio
    async def test_get_entries(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        entries = await l_make.n_entries(loaded_feed, n=4)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        failed_entries = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)

        assert set(entries) <= set(failed_entries)

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId) -> None:
        while True:
            failed_entries = await operations.get_failed_entries(execute, fake_processor_id, limit=1000)
            await operations.remove_failed_entries(execute, fake_processor_id, failed_entries)

            if not failed_entries:
                break

        failed_entries = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)

        assert not failed_entries

    @pytest.mark.asyncio
    async def test_idempotency(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        entries = await l_make.n_entries(loaded_feed, n=13)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        failed_entries_1 = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        failed_entries_2 = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)

        assert failed_entries_1 == failed_entries_2


class TestRemoveFailedEntries:
    @pytest.mark.asyncio
    async def test_remove_entries(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        entries = await l_make.n_entries(loaded_feed, n=13)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        entries_to_remove = list(entries)[:5]

        async with TableSizeDelta("ln_failed_entries", delta=-5):
            await operations.remove_failed_entries(execute, fake_processor_id, entries_to_remove)

        failed_entries = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)

        assert set(entries_to_remove) & set(failed_entries) == set()

    @pytest.mark.asyncio
    async def test_remove_non_existing_entries(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        entries = await l_make.n_entries(loaded_feed, n=5)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        entries_to_remove = [new_entry_id(), new_entry_id()]

        async with TableSizeNotChanged("ln_failed_entries"):
            await operations.remove_failed_entries(execute, fake_processor_id, entries_to_remove)


class TestCountFailedEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId) -> None:
        await helpers.clean_failed_storage([fake_processor_id, another_fake_processor_id])

        counts = await operations.count_failed_entries()

        assert fake_processor_id not in counts
        assert another_fake_processor_id not in counts

    @pytest.mark.asyncio
    async def test_some_entries(
        self, saved_feed: Feed, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        await helpers.clean_failed_storage([fake_processor_id, another_fake_processor_id])

        entries = await l_make.n_entries(saved_feed, n=3)
        entries_list = list(entries)

        await operations.add_entries_to_failed_storage(fake_processor_id, [entries_list[0], entries_list[1]])
        await operations.add_entries_to_failed_storage(
            another_fake_processor_id, [entry_id for entry_id in entries_list]
        )

        counts = await operations.count_failed_entries()

        assert counts[fake_processor_id] == 2
        assert counts[another_fake_processor_id] == 3
