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
from ffun.loader.operations import check_proxy, get_proxy_states, is_proxy_available, load_content, update_proxy_states
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


class TestLoadContent:
    @pytest.mark.parametrize(
        "bytes_content, expected_headers",
        [
            (b"test-response", {}),
            (
                b"\x1f\x8b\x08\x00v\x18Sf\x02\xff+I-.\xd1-J-.\xc8\xcf+N\x05\x00\xfe\xebMu\r\x00\x00\x00",
                {"Content-Encoding": "gzip"},
            ),
            (b"x\x9c+I-.\xd1-J-.\xc8\xcf+N\x05\x00%A\x05]", {"Content-Encoding": "deflate"}),
            # TODO: add zstd support after upgrading HTTPX to the last version
            pytest.param(
                b"(\xb5/\xfd \ri\x00\x00test-response",
                {"Content-Encoding": "zstd"},
                marks=[pytest.mark.xfail(reason="zstd is not supported")],
            ),
            (b"\x1b\x0c\x00\xf8\xa5[\xca\xe6\xe8\x84+\xa1\xc66", {"Content-Encoding": "br"}),
        ],
        ids=["plain", "gzip", "deflate", "zstd", "br"],
    )
    @pytest.mark.asyncio
    async def test_compressing_support(
        self, respx_mock: MockRouter, bytes_content: bytes, expected_headers: dict[str, str]
    ) -> None:
        expected_content = "test-response"

        mocked_response = httpx.Response(200, headers=expected_headers, content=bytes_content)

        respx_mock.get("/test").mock(return_value=mocked_response)

        response = await load_content(
            url=str_to_absolute_url("http://example.com/test"), proxy=Proxy(name="test", url=None), user_agent="test"
        )

        assert response.text == expected_content

    @pytest.mark.asyncio
    async def test_accept_encoding_header(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock()

        await load_content(
            url=str_to_absolute_url("http://example.com/test"), proxy=Proxy(name="test", url=None), user_agent="test"
        )

        assert respx_mock.calls[0].request.headers["Accept-Encoding"] == "br;q=1.0, gzip;q=0.9, deflate;q=0.8"

    @pytest.mark.asyncio
    async def test_expected_error(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock(side_effect=httpx.ConnectTimeout("some message"))

        with capture_logs() as logs:
            with pytest.raises(errors.LoadError) as expected_error:
                await load_content(
                    url=str_to_absolute_url("http://example.com/test"),
                    proxy=Proxy(name="test", url=None),
                    user_agent="test",
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
                    user_agent="test",
                )

        assert expected_error.value.feed_error_code == FeedError.network_unknown

        assert_logs(logs, error_while_loading_feed=1)
        assert_logs_levels(logs, error_while_loading_feed="error")
