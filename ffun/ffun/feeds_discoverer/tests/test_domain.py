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


class TestDiscoverCreateSoup:

    @pytest.mark.xfail(reason="need to find a case when BeautifulSoup raises an exception")
    @pytest.mark.asyncio
    async def test_not_html(self) -> None:
        context = Context(raw_url="http://localhost/test",
                          content="some text content")

        new_context, result = await _discover_create_soup(context)

        assert new_context == context
        assert result == Result(feeds=[], status=Status.not_html)

    @pytest.mark.asyncio
    async def test_html(self, raw_feed_content: str) -> None:
        context = Context(raw_url="http://localhost/test",
                          content="<html></html>")

        new_context, result = await _discover_create_soup(context)

        assert new_context.soup is not None
        assert result is None


class TestDiscoverExtractFeedsFromLinks:

    @pytest.mark.asyncio
    async def test_no_links(self) -> None:
        intro_context = Context(raw_url="http://localhost/test",
                                url="http://localhost/test",
                                content="<html></html>")

        context, result = await _discover_create_soup(intro_context)

        new_context, result = await _discover_extract_feeds_from_links(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_links(self) -> None:
        # "author", "help", "icon", "license", "pingback", "search", "stylesheet"
        html = '''
        <html>
          <head>
            <link href="http://localhost/feed1">

            <!-- ignore these -->
            <link rel="author" href="http://localhost/feed2">
            <link rel="help" href="http://localhost/feed3">
            <link rel="icon" href="http://localhost/feed4">
            <link rel="license" href="http://localhost/feed5">
            <link rel="pingback" href="http://localhost/feed6">
            <link rel="search" href="http://localhost/feed7">
            <link rel="stylesheet" href="http://localhost/feed8">

            <link rel="random-rel" href="http://localhost/feed9">
            <link rel="random-rel" href="/feed10">
            <link rel="random-rel" href="feed11">
         </head>
         <body>
           <link href="http://localhost/feed12">
        </body>
        </html>
        '''

        intro_context = Context(raw_url="http://localhost/test/xxx",
                          url="http://localhost/test/xxx",
                          content=html)

        context, result = await _discover_create_soup(intro_context)

        new_context, result = await _discover_extract_feeds_from_links(context)

        expected_links = {"http://localhost/feed1",
                          "http://localhost/feed9",
                          "http://localhost/feed10",
                          "http://localhost/test/feed11",
                          "http://localhost/feed12"}

        assert new_context == context.replace(candidate_urls=expected_links)
        assert result is None
