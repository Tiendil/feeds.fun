import pytest

import httpx
from respx.router import MockRouter
from ffun.domain.domain import new_feed_id
from ffun.feeds_discoverer.domain import _discover_normalize_url, _discover_load_url, _discover_extract_feed_info, _discover_create_soup, _discover_extract_feeds_from_links, _discover_extract_feeds_from_anchors, _discover_check_candidate_links, _discover_stop_recursion, _discoverers, discover
from ffun.feeds_discoverer.entities import Result, Context, Status, Discoverer


class TestDiscoverNormalizeUrl:

    @pytest.mark.asyncio
    async def test_wrong_url(self) -> None:
        context = Context(raw_url="wrong_url")

        new_context, result = await _discover_normalize_url(context)

        assert new_context == context
        assert result == Result(feeds=[], status=Status.incorrect_url)

    @pytest.mark.asyncio
    async def test_good_url(self) -> None:
        context = Context(raw_url="https://example.com?")

        new_context, result = await _discover_normalize_url(context)

        assert new_context == context.replace(url="https://example.com")
        assert result is None


class TestDiscoverLoadUrl:

    @pytest.mark.asyncio
    async def test_error(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock(side_effect=httpx.ConnectTimeout("some message"))

        context = Context(raw_url="http://localhost/test",
                          url="http://localhost/test")

        new_context, result = await _discover_load_url(context)

        assert new_context == context
        assert result == Result(feeds=[], status=Status.cannot_access_url)

    @pytest.mark.asyncio
    async def test_success(self, respx_mock: MockRouter) -> None:
        expected_content = "test-response"

        mocked_response = httpx.Response(200, content=expected_content)

        respx_mock.get("/test").mock(return_value=mocked_response)

        context = Context(raw_url="http://localhost/test",
                          url="http://localhost/test")

        new_context, result = await _discover_load_url(context)

        assert new_context == context.replace(content=expected_content)
        assert result is None


class TestDiscoverExtractFeedInfo:

    @pytest.mark.asyncio
    async def test_not_a_feed(self) -> None:
        context = Context(raw_url="http://localhost/test",
                          url="http://localhost/test",
                          content="some text content")

        new_context, result = await _discover_extract_feed_info(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_a_feed(self, raw_feed_content: str) -> None:

        context = Context(raw_url="http://localhost/test",
                          url="http://localhost/test",
                          content=raw_feed_content)

        new_context, result = await _discover_extract_feed_info(context)

        assert new_context == context

        assert result.status == Status.feeds_found
        assert len(result.feeds) == 1
        assert result.feeds[0].url == "http://localhost/test"
