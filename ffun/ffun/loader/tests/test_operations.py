import uuid

import pytest

from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.loader.entities import ProxyState
from ffun.loader.operations import check_proxy, get_proxy_states, is_proxy_available, update_proxy_states
from ffun.loader.settings import Proxy


class TestUpdateProxyStates:
    @pytest.mark.asyncio
    async def test_nothing_to_update(self) -> None:
        async with TableSizeNotChanged("lr_proxy_states"):
            await update_proxy_states({})

    @pytest.mark.asyncio
    async def test_first_time_updated(self) -> None:
        states = {
            uuid.uuid4().hex: ProxyState.available,
            uuid.uuid4().hex: ProxyState.suspended,
            uuid.uuid4().hex: ProxyState.available,
        }

        async with TableSizeDelta("lr_proxy_states", delta=len(states)):
            await update_proxy_states(states)

        loaded_states = await get_proxy_states(names=list(states.keys()))

        assert loaded_states == states

    @pytest.mark.asyncio
    async def test_second_updated(self) -> None:
        names = [uuid.uuid4().hex for _ in range(4)]

        states = {names[0]: ProxyState.available, names[1]: ProxyState.suspended, names[2]: ProxyState.available}

        await update_proxy_states(states)

        second_states = {
            names[1]: ProxyState.available,
            names[2]: ProxyState.available,
            names[3]: ProxyState.suspended,
        }

        async with TableSizeDelta("lr_proxy_states", delta=1):
            await update_proxy_states(second_states)

        loaded_states = await get_proxy_states(names=names)

        assert loaded_states == {
            names[0]: ProxyState.available,
            names[1]: ProxyState.available,
            names[2]: ProxyState.available,
            names[3]: ProxyState.suspended,
        }


# Most of the functionality are checked in other code
class TestGetProxyStates:
    @pytest.mark.asyncio
    async def test_default_to_available(self) -> None:
        names = [uuid.uuid4().hex for _ in range(4)]

        await update_proxy_states({names[0]: ProxyState.suspended, names[2]: ProxyState.available})

        states = await get_proxy_states(names)

        assert states == {
            names[0]: ProxyState.suspended,
            names[1]: ProxyState.available,
            names[2]: ProxyState.available,
            names[3]: ProxyState.available,
        }


class TestCheckProxy:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        url = "https://www.google.com"
        user_agent = "Mozilla/5.0"

        assert await check_proxy(proxy, url, user_agent)

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        url = "localhost:1"
        user_agent = "Mozilla/5.0"

        assert not await check_proxy(proxy, url, user_agent)


class TestIsProxyAvailable:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        anchors = ["https://www.google.com", "https://www.amazon.com"]
        user_agent = "Mozilla/5.0"

        assert await is_proxy_available(proxy, anchors, user_agent)

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        anchors = ["localhost:1", "localhost:2"]
        user_agent = "Mozilla/5.0"

        assert not await is_proxy_available(proxy, anchors, user_agent)
