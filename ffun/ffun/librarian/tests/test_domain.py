import datetime
import uuid
from itertools import chain

import pytest
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.librarian import errors, operations
from ffun.librarian.domain import push_entries_and_move_pointer
from ffun.librarian.entities import ProcessorPointer
from ffun.library import operations as l_operations
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make


class TestPushEntriesAndMovePointer:

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: int) -> None:
        pointer = await operations.get_pointer(fake_processor_id)

        async with TableSizeNotChanged("ln_processors_queue"):
            await push_entries_and_move_pointer(pointer, [])

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert loaded_pointer == pointer

    @pytest.mark.asyncio
    async def test_push_entries(self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        original_pointer = await operations.get_pointer(fake_processor_id)

        entries = [cataloged_entry, another_cataloged_entry]
        entries.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        last_entry = entries[-1]

        next_pointer = ProcessorPointer(processor_id=fake_processor_id,
                                        pointer_created_at=last_entry.cataloged_at,
                                        pointer_entry_id=last_entry.id)

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await push_entries_and_move_pointer(next_pointer, [cataloged_entry.id, another_cataloged_entry.id])

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert loaded_pointer == next_pointer
        assert loaded_pointer != original_pointer
