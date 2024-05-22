import datetime
import uuid

import pytest
from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.librarian import errors, operations
from ffun.library.tests import make as l_make
from ffun.loader.entities import ProxyState
from ffun.loader.operations import get_proxy_states, update_proxy_states


# def assert_is_new_pointer(pointer: ProcessorPointer, processor_id: int) -> None:
#     assert pointer.processor_id == processor_id
#     assert pointer.pointer_created_at == datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
#     assert pointer.pointer_entry_id == uuid.UUID("00000000-0000-0000-0000-000000000000")


class TestUpdateProxyStates:

    @pytest.mark.asyncio
    async def test_nothing_to_update(self) -> None:
        async with TableSizeNotChanged("lr_proxy_states"):
            await update_proxy_states({})

    @pytest.mark.asyncio
    async def test_first_time_updated(self) -> None:
        states = {uuid.uuid4().hex: ProxyState.available,
                  uuid.uuid4().hex: ProxyState.suspended,
                  uuid.uuid4().hex: ProxyState.available}

        async with TableSizeDelta("lr_proxy_states", delta=len(states)):
            await update_proxy_states(states)

        loaded_states = await get_proxy_states(names=list(states.keys()))

        assert loaded_states == states

    @pytest.mark.asyncio
    async def test_second_updated(self) -> None:
        names = [uuid.uuid4().hex for _ in range(4)]

        states = {names[0]: ProxyState.available,
                  names[1]: ProxyState.suspended,
                  names[2]: ProxyState.available}

        await update_proxy_states(states)

        second_states = {names[1]: ProxyState.available,
                         names[2]: ProxyState.available,
                         names[3]: ProxyState.suspended}

        async with TableSizeDelta("lr_proxy_states", delta=1):
            await update_proxy_states(second_states)

        loaded_states = await get_proxy_states(names=names)

        assert loaded_states == {names[0]: ProxyState.available,
                                 names[1]: ProxyState.available,
                                 names[2]: ProxyState.available,
                                 names[3]: ProxyState.suspended}


# Most of the functionality are checked in other code
class TestGetProxyStates:

    @pytest.mark.asyncio
    async def test_default_to_available(self) -> None:
        names = [uuid.uuid4().hex for _ in range(4)]

        await update_proxy_states({names[0]: ProxyState.suspended,
                                   names[2]: ProxyState.available})

        states = await get_proxy_states(names)

        assert states == {names[0]: ProxyState.suspended,
                          names[1]: ProxyState.available,
                          names[2]: ProxyState.available,
                          names[3]: ProxyState.available}
