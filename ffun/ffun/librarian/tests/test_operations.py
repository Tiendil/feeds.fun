import datetime
import uuid
from itertools import chain

import pytest
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.librarian import errors, operations
from ffun.librarian.entities import ProcessorPointer
from ffun.library import operations as l_operations
from ffun.library.tests import make as l_make


def assert_is_new_pointer(pointer: ProcessorPointer, processor_id) -> None:
    assert pointer.processor_id == processor_id
    assert pointer.pointer_created_at == datetime.datetime(1970, 1, 1, 0, 0)
    assert pointer.pointer_entry_id == uuid.UUID('00000000-0000-0000-0000-000000000000')


class TestCreatePointer:

    @pytest.mark.asyncio
    async def test_new_pointer(self, fake_processor_id: int) -> None:
        await operations.delete_pointer(fake_processor_id)

        async with TableSizeDelta('ln_processor_pointers', delta=1):
            pointer = await operations.create_pointer(fake_processor_id)

        assert_is_new_pointer(pointer, fake_processor_id)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert loaded_pointer.processor_id == fake_processor_id

    @pytest.mark.asyncio
    async def test_existing_pointer(self, fake_processor_id: int) -> None:
        pointer = await operations.create_pointer(fake_processor_id)

        async with TableSizeNotChanged('ln_processor_pointers'):
            second_pointer = await operations.create_pointer(fake_processor_id)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert pointer == second_pointer == loaded_pointer


# the base behavior of the get_pointer function is checked in other tests, that use it
class TestGetPointer:

    @pytest.mark.asyncio
    async def test_create_if_not_exists(self, fake_processor_id: int) -> None:
        await operations.delete_pointer(fake_processor_id)

        async with TableSizeDelta('ln_processor_pointers', delta=1):
            pointer = await operations.get_pointer(fake_processor_id)

        assert_is_new_pointer(pointer, fake_processor_id)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert loaded_pointer.processor_id == fake_processor_id


class TestDeletePointer:

    @pytest.mark.asyncio
    async def test_existing_pointer(self, fake_processor_id: int) -> None:
        pointer = await operations.create_pointer(fake_processor_id)

        pointer.replace(pointer_entry_id=uuid.uuid4())

        await operations.save_pointer(execute, pointer)

        async with TableSizeDelta('ln_processor_pointers', delta=-1):
            await operations.delete_pointer(fake_processor_id)

        new_pointer = await operations.get_pointer(fake_processor_id)

        assert_is_new_pointer(new_pointer, fake_processor_id)

    @pytest.mark.asyncio
    async def test_no_pointer(self, fake_processor_id: int) -> None:
        await operations.delete_pointer(fake_processor_id)

        async with TableSizeNotChanged('ln_processor_pointers'):
            await operations.delete_pointer(fake_processor_id)


class TestSavePointer:

    @pytest.mark.asyncio
    async def test_no_pointer(self, fake_processor_id: int) -> None:
        await operations.delete_pointer(fake_processor_id)

        pointer = ProcessorPointer(
            processor_id=fake_processor_id,
            pointer_entry_id=uuid.uuid4(),
            pointer_created_at=datetime.datetime.now(),
        )

        async with TableSizeNotChanged('ln_processor_pointers'):
            with pytest.raises(errors.CanNotSaveUnexistingPointer):
                await operations.save_pointer(execute, pointer)

    @pytest.mark.asyncio
    async def test_existing_pointer(self, fake_processor_id: int) -> None:
        pointer = await operations.create_pointer(fake_processor_id)

        new_pointer = pointer.replace(pointer_created_at=datetime.datetime.now(),
                                      pointer_entry_id=uuid.uuid4())

        async with TableSizeNotChanged('ln_processor_pointers'):
            await operations.save_pointer(execute, new_pointer)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert new_pointer == loaded_pointer


class TestPushEntriesToProcessorQueue:

    @pytest.mark.parametrize('entries_count', [0, 1, 3, 10])
    @pytest.mark.asyncio
    async def test_push_entry(self, loaded_feed_id: uuid.UUID, entries_count: int, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, n=entries_count + 5)

        entries_to_push = list(entries)[:entries_count]

        async with TableSizeDelta('ln_processors_queue', delta=entries_count):
            await operations.push_entries_to_processor_queue(execute, fake_processor_id, entries_to_push)

        entries_in_queue = await operations.get_entries_to_process(fake_processor_id, n=entries_count + 5)

        assert set(entries_to_push) == set(entries_in_queue)


class TestGetEntriesToProcess:

    @pytest.mark.asyncio
    async def test_get_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, n=13)

        await operations.push_entries_to_processor_queue(execute, fake_processor_id, list(entries))

        received_entries = set()

        while True:
            new_entries_ids = await operations.get_entries_to_process(fake_processor_id, n=3)
            received_entries.update(new_entries_ids)
            await operations.remove_entries_from_processor_queue(fake_processor_id, new_entries_ids)

            if len(received_entries) == len(entries):
                assert len(new_entries_ids) == 13 % 3
                break

        assert set(entries) == received_entries

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        entries = await operations.get_entries_to_process(fake_processor_id, n=3)

        assert not entries

    @pytest.mark.asyncio
    async def test_idempotency(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, n=13)

        await operations.push_entries_to_processor_queue(execute, fake_processor_id, list(entries))

        entries_ids_1 = await operations.get_entries_to_process(fake_processor_id, n=3)
        entries_ids_2 = await operations.get_entries_to_process(fake_processor_id, n=3)

        assert entries_ids_1 == entries_ids_2


class TestRemoveEntriesFromProcessorQueue:

    @pytest.mark.asyncio
    async def test_remove_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, n=13)

        await operations.push_entries_to_processor_queue(execute, fake_processor_id, list(entries))

        entries_to_remove = list(entries)[:5]

        async with TableSizeDelta('ln_processors_queue', delta=-5):
            await operations.remove_entries_from_processor_queue(fake_processor_id, entries_to_remove)

        entries_in_queue = await operations.get_entries_to_process(fake_processor_id, n=13)

        assert len(entries_in_queue) == 8

        assert set(entries_to_remove) & set(entries_in_queue) == set()

    @pytest.mark.asyncio
    async def test_remove_non_existing_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed_id, n=13)

        await operations.push_entries_to_processor_queue(execute, fake_processor_id, list(entries))

        entries_to_remove = [uuid.uuid4(), uuid.uuid4()]

        await operations.remove_entries_from_processor_queue(fake_processor_id, entries_to_remove)

        entries_in_queue = await operations.get_entries_to_process(fake_processor_id, n=13)

        assert set(entries) == set(entries_in_queue)


class TestClearProcessorQueue:
    # checked in other tests
    pass


class TestAddEntriesToFailedStorage:

    @pytest.mark.asyncio
    async def test_add_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        entries = await l_make.n_entries(loaded_feed_id, n=13)

        entries_to_add = list(entries)[:5]

        async with TableSizeDelta('ln_failed_entries', delta=5):
            await operations.add_entries_to_failed_storage(fake_processor_id, entries_to_add)

        failed_entries = await operations.get_failed_entries(fake_processor_id, n=100500)

        assert set(entries_to_add) <= set(failed_entries)


class TestGetFailedEntries:

    @pytest.mark.asyncio
    async def test_get_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        entries = await l_make.n_entries(loaded_feed_id, n=4)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        failed_entries = await operations.get_failed_entries(fake_processor_id, n=100500)

        assert set(entries) <= set(failed_entries)

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: int) -> None:
        while True:
            failed_entries = await operations.get_failed_entries(fake_processor_id, n=1000)
            await operations.remove_failed_entries(fake_processor_id, failed_entries)

            if not failed_entries:
                break

        failed_entries = await operations.get_failed_entries(fake_processor_id, n=100500)

        assert not failed_entries

    @pytest.mark.asyncio
    async def test_idempotency(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        entries = await l_make.n_entries(loaded_feed_id, n=13)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        failed_entries_1 = await operations.get_failed_entries(fake_processor_id, n=100500)
        failed_entries_2 = await operations.get_failed_entries(fake_processor_id, n=100500)

        assert failed_entries_1 == failed_entries_2


class TestRemoveFailedEntries:

    @pytest.mark.asyncio
    async def test_remove_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        entries = await l_make.n_entries(loaded_feed_id, n=13)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        entries_to_remove = list(entries)[:5]

        async with TableSizeDelta('ln_failed_entries', delta=-5):
            await operations.remove_failed_entries(fake_processor_id, entries_to_remove)

        failed_entries = await operations.get_failed_entries(fake_processor_id, n=100500)

        assert set(entries_to_remove) & set(failed_entries) == set()

    @pytest.mark.asyncio
    async def test_remove_non_existing_entries(self, loaded_feed_id: uuid.UUID, fake_processor_id: int) -> None:
        entries = await l_make.n_entries(loaded_feed_id, n=5)

        await operations.add_entries_to_failed_storage(fake_processor_id, list(entries))

        entries_to_remove = [uuid.uuid4(), uuid.uuid4()]

        async with TableSizeNotChanged('ln_failed_entries'):
            await operations.remove_failed_entries(fake_processor_id, entries_to_remove)
