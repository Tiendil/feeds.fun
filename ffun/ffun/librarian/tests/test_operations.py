import datetime
import uuid
from itertools import chain

import pytest
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.librarian import errors, operations
from ffun.librarian.entities import ProcessorPointer


fake_processor_id = 11042


def assert_is_new_pointer(pointer: ProcessorPointer, processor_id) -> None:
    assert pointer.processor_id == processor_id
    assert pointer.pointer_created_at == datetime.datetime(1970, 1, 1, 0, 0)
    assert pointer.pointer_entry_id == uuid.UUID('00000000-0000-0000-0000-000000000000')


class TestCreatePointer:

    @pytest.mark.asyncio
    async def test_new_pointer(self) -> None:
        await operations.delete_pointer(fake_processor_id)

        async with TableSizeDelta('ln_processor_pointers', delta=1):
            pointer = await operations.create_pointer(fake_processor_id)

        assert_is_new_pointer(pointer, fake_processor_id)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert loaded_pointer.processor_id == fake_processor_id

    @pytest.mark.asyncio
    async def test_existing_pointer(self) -> None:
        pointer = await operations.create_pointer(fake_processor_id)

        async with TableSizeNotChanged('ln_processor_pointers'):
            second_pointer = await operations.create_pointer(fake_processor_id)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert pointer == second_pointer == loaded_pointer


# the base behavior of the get_pointer function is checked in other tests, that use it
class TestGetPointer:

    @pytest.mark.asyncio
    async def test_create_if_not_exists(self) -> None:
        await operations.delete_pointer(fake_processor_id)

        async with TableSizeDelta('ln_processor_pointers', delta=1):
            pointer = await operations.get_pointer(fake_processor_id)

        assert_is_new_pointer(pointer, fake_processor_id)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert loaded_pointer.processor_id == fake_processor_id


class TestDeletePointer:

    @pytest.mark.asyncio
    async def test_existing_pointer(self) -> None:
        pointer = await operations.create_pointer(fake_processor_id)

        pointer.replace(pointer_entry_id=uuid.uuid4())

        await operations.save_pointer(pointer)

        async with TableSizeDelta('ln_processor_pointers', delta=-1):
            await operations.delete_pointer(fake_processor_id)

        new_pointer = await operations.get_pointer(fake_processor_id)

        assert_is_new_pointer(new_pointer, fake_processor_id)

    @pytest.mark.asyncio
    async def test_no_pointer(self) -> None:
        await operations.delete_pointer(fake_processor_id)

        async with TableSizeNotChanged('ln_processor_pointers'):
            await operations.delete_pointer(fake_processor_id)


class TestSavePointer:

    @pytest.mark.asyncio
    async def test_no_pointer(self) -> None:
        await operations.delete_pointer(fake_processor_id)

        pointer = ProcessorPointer(
            processor_id=fake_processor_id,
            pointer_entry_id=uuid.uuid4(),
            pointer_created_at=datetime.datetime.now(),
        )

        async with TableSizeNotChanged('ln_processor_pointers'):
            with pytest.raises(errors.CanNotSaveUnexistingPointer):
                await operations.save_pointer(pointer)

    @pytest.mark.asyncio
    async def test_existing_pointer(self) -> None:
        pointer = await operations.create_pointer(fake_processor_id)

        new_pointer = pointer.replace(pointer_created_at=datetime.datetime.now(),
                                      pointer_entry_id=uuid.uuid4())

        async with TableSizeNotChanged('ln_processor_pointers'):
            await operations.save_pointer(new_pointer)

        loaded_pointer = await operations.get_pointer(fake_processor_id)

        assert new_pointer == loaded_pointer
