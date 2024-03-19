import datetime
import uuid
from itertools import chain

import pytest
from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.librarian import errors, operations
from ffun.librarian.domain import plan_processor_queue, push_entries_and_move_pointer
from ffun.librarian.entities import ProcessorPointer
from ffun.librarian.tests import make
from ffun.library import operations as l_operations
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make


class TestPushEntriesAndMovePointer:

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: int) -> None:
        pointer = await operations.get_or_create_pointer(fake_processor_id)

        async with TableSizeNotChanged("ln_processors_queue"):
            await push_entries_and_move_pointer(pointer, [])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == pointer

    @pytest.mark.asyncio
    async def test_push_entries(self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        original_pointer = await operations.get_or_create_pointer(fake_processor_id)

        entries = [cataloged_entry, another_cataloged_entry]
        entries.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        last_entry = entries[-1]

        next_pointer = ProcessorPointer(processor_id=fake_processor_id,
                                        pointer_created_at=last_entry.cataloged_at,
                                        pointer_entry_id=last_entry.id)

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await push_entries_and_move_pointer(next_pointer, [cataloged_entry.id, another_cataloged_entry.id])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == next_pointer
        assert loaded_pointer != original_pointer


class TestPushEntriesAndMovePointer:

    @pytest.mark.asyncio
    async def test_no_new_entries(self, fake_processor_id: int) -> None:
        pointer = await make.end_processor_pointer(fake_processor_id)

        next_pointer = pointer.replace(pointer_created_at=utils.now())

        async with TableSizeNotChanged("ln_processors_queue"):
            await push_entries_and_move_pointer(next_pointer, [])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == next_pointer

    @pytest.mark.asyncio
    async def test_entries_found_and_moved(self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        entries = [cataloged_entry, another_cataloged_entry]
        entries.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        pointer = await make.end_processor_pointer(fake_processor_id)

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await push_entries_and_move_pointer(pointer, [cataloged_entry.id, another_cataloged_entry.id])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == pointer


class TestPlanProcessorQueue:

    @pytest.mark.asyncio
    async def test_no_new_entries(self, fake_processor_id: int, cataloged_entry: Entry) -> None:
        pointer = await make.end_processor_pointer(fake_processor_id)

        async with TableSizeNotChanged("ln_processors_queue"):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=100)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == pointer

    @pytest.mark.asyncio
    async def test_move_pointer_to_the_end(self, loaded_feed_id: int, fake_processor_id: int) -> None:
        await make.end_processor_pointer(1)

        entries = await l_make.n_entries(loaded_feed_id, 3)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        async with TableSizeDelta("ln_processors_queue", delta=3):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=100)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(processor_id=fake_processor_id,
                                                  pointer_created_at=entries_list[-1].cataloged_at,
                                                  pointer_entry_id=entries_list[-1].id)

    @pytest.mark.asyncio
    async def test_move_pointer_to_not_the_end(self, loaded_feed_id: int, fake_processor_id: int) -> None:
        await make.end_processor_pointer(1)

        entries = await l_make.n_entries(loaded_feed_id, 3)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=2)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(processor_id=fake_processor_id,
                                                  pointer_created_at=entries_list[-2].cataloged_at,
                                                  pointer_entry_id=entries_list[-2].id)

    @pytest.mark.asyncio
    async def test_chunk_limit(self, loaded_feed_id: int, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await make.end_processor_pointer(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, 5)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        async with TableSizeDelta("ln_processors_queue", delta=3):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=3)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(processor_id=fake_processor_id,
                                                  pointer_created_at=entries_list[2].cataloged_at,
                                                  pointer_entry_id=entries_list[2].id)

    @pytest.mark.asyncio
    async def test_do_not_push_if_there_are_enough_entries(self, loaded_feed_id: int, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await make.end_processor_pointer(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, 5)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=3)

        async with TableSizeNotChanged("ln_processors_queue"):
            await plan_processor_queue(fake_processor_id, fill_when_below=3, chunk=2)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(processor_id=fake_processor_id,
                                                  pointer_created_at=entries_list[2].cataloged_at,
                                                  pointer_entry_id=entries_list[2].id)
