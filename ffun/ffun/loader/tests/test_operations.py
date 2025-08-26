import uuid

import httpx
import pytest
from respx.router import MockRouter
from structlog.testing import capture_logs

from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs,
    assert_logs_have_no_errors,
    assert_logs_levels,
)
from ffun.domain.urls import str_to_absolute_url
from ffun.feeds.entities import FeedError
from ffun.loader import errors
from ffun.loader.entities import ProxyState
from ffun.loader.operations import (
    check_proxy,
    get_proxy_states,
    is_proxy_available,
    load_content,
    update_proxy_states,
)
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

        assert await check_proxy(proxy, url)

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        url = "localhost:1"

        assert not await check_proxy(proxy, url)


class TestIsProxyAvailable:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        anchors = ["https://www.google.com", "https://www.amazon.com"]

        assert await is_proxy_available(proxy, anchors)

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        proxy = Proxy(name=uuid.uuid4().hex, url=None)
        anchors = ["localhost:1", "localhost:2"]

        assert not await is_proxy_available(proxy, anchors)


class TestLoadContent:

    @pytest.mark.asyncio
    async def test_expected_error(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock(side_effect=httpx.ConnectTimeout("some message"))

        with capture_logs() as logs:
            with pytest.raises(errors.LoadError) as expected_error:
                await load_content(
                    url=str_to_absolute_url("http://example.com/test"),
                    proxy=Proxy(name="test", url=None),
                )

        assert expected_error.value.feed_error_code == FeedError.network_connection_timeout

        assert_logs(logs, error_while_loading_feed=0)
        assert_logs_have_no_errors(logs)

    @pytest.mark.asyncio
    async def test_unexpected_error(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock(side_effect=Exception("some message"))

        with capture_logs() as logs:
            with pytest.raises(errors.LoadError) as expected_error:
                await load_content(
                    url=str_to_absolute_url("http://example.com/test"),
                    proxy=Proxy(name="test", url=None),
                )

        assert expected_error.value.feed_error_code == FeedError.network_unknown

        assert_logs(logs, error_while_loading_feed=1)
        assert_logs_levels(logs, error_while_loading_feed="error")
