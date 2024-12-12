import httpx
import pytest
from respx.router import MockRouter

from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.domain import (
    _discover_adjust_url,
    _discover_create_soup,
    _discover_extract_feed_info,
    _discover_extract_feeds_from_links,
    _discover_extract_feeds_from_anchors,
    _discover_load_url,
)
from ffun.feeds_discoverer.entities import Context, Result, Status


class TestDiscoverAdjustUrl:

    @pytest.mark.asyncio
    async def test_wrong_url(self) -> None:
        context = Context(raw_url=UnknownUrl("wrong_url"))

        new_context, result = await _discover_adjust_url(context)

        assert new_context == context
        assert result == Result(feeds=[], status=Status.incorrect_url)

    @pytest.mark.asyncio
    async def test_good_url(self) -> None:
        context = Context(raw_url=UnknownUrl("https://example.com?"))

        new_context, result = await _discover_adjust_url(context)

        assert new_context == context.replace(url=AbsoluteUrl("https://example.com"))
        assert result is None


class TestDiscoverLoadUrl:

    @pytest.mark.asyncio
    async def test_error(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock(side_effect=httpx.ConnectTimeout("some message"))

        context = Context(
            raw_url=UnknownUrl("http://localhost/test"), url=str_to_absolute_url("http://localhost/test")
        )

        new_context, result = await _discover_load_url(context)

        assert new_context == context
        assert result == Result(feeds=[], status=Status.cannot_access_url)

    @pytest.mark.asyncio
    async def test_success(self, respx_mock: MockRouter) -> None:
        expected_content = "test-response"

        mocked_response = httpx.Response(200, content=expected_content)

        respx_mock.get("/test").mock(return_value=mocked_response)

        context = Context(
            raw_url=UnknownUrl("http://localhost/test"), url=str_to_absolute_url("http://localhost/test")
        )

        new_context, result = await _discover_load_url(context)

        assert new_context == context.replace(content=expected_content)
        assert result is None


class TestDiscoverExtractFeedInfo:

    @pytest.mark.asyncio
    async def test_not_a_feed(self) -> None:
        context = Context(
            raw_url=UnknownUrl("http://localhost/test"),
            url=str_to_absolute_url("http://localhost/test"),
            content="some text content",
        )

        new_context, result = await _discover_extract_feed_info(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_a_feed(self, raw_feed_content: str) -> None:

        context = Context(
            raw_url=UnknownUrl("http://localhost/test"),
            url=str_to_absolute_url("http://localhost/test"),
            content=raw_feed_content,
        )

        new_context, result = await _discover_extract_feed_info(context)

        assert result is not None

        assert new_context == context

        assert result.status == Status.feeds_found
        assert len(result.feeds) == 1
        assert result.feeds[0].url == AbsoluteUrl("http://localhost/test")


class TestDiscoverCreateSoup:

    @pytest.mark.xfail(reason="need to find a case when BeautifulSoup raises an exception")
    @pytest.mark.asyncio
    async def test_not_html(self) -> None:
        context = Context(raw_url=UnknownUrl("http://localhost/test"), content="some text content")

        new_context, result = await _discover_create_soup(context)

        assert new_context == context
        assert result == Result(feeds=[], status=Status.not_html)

    @pytest.mark.asyncio
    async def test_html(self, raw_feed_content: str) -> None:
        context = Context(raw_url=UnknownUrl("http://localhost/test"), content="<html></html>")

        new_context, result = await _discover_create_soup(context)

        assert new_context.soup is not None
        assert result is None


class TestDiscoverExtractFeedsFromLinks:

    @pytest.mark.asyncio
    async def test_no_links(self) -> None:
        intro_context = Context(
            raw_url=UnknownUrl("http://localhost/test"),
            url=str_to_absolute_url("http://localhost/test"),
            content="<html></html>",
        )

        context, result = await _discover_create_soup(intro_context)

        new_context, result = await _discover_extract_feeds_from_links(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_links(self) -> None:
        # "author", "help", "icon", "license", "pingback", "search", "stylesheet"
        html = """
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
           <a href="http://localhost/feed13"></a>
        </body>
        </html>
        """

        intro_context = Context(
            raw_url=UnknownUrl("http://localhost/test/xxx"),
            url=str_to_absolute_url("http://localhost/test/xxx"),
            content=html,
        )

        context, result = await _discover_create_soup(intro_context)

        new_context, result = await _discover_extract_feeds_from_links(context)

        expected_links = {
            AbsoluteUrl("http://localhost/feed1"),
            AbsoluteUrl("http://localhost/feed9"),
            AbsoluteUrl("http://localhost/feed10"),
            AbsoluteUrl("http://localhost/test/feed11"),
            AbsoluteUrl("http://localhost/feed12"),
        }

        assert new_context == context.replace(candidate_urls=expected_links)
        assert result is None


class TestDiscoverExtractFeedsFromAnchors:

    @pytest.mark.asyncio
    async def test_no_anchorts(self) -> None:
        intro_context = Context(
            raw_url=UnknownUrl("http://localhost/test"),
            url=str_to_absolute_url("http://localhost/test"),
            content="<html></html>",
        )

        context, result = await _discover_create_soup(intro_context)

        new_context, result = await _discover_extract_feeds_from_anchors(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_has_anchors(self) -> None:

        html = """
        <html>
          <head>
            <link href="http://localhost/feed1">
         </head>
         <body>
           <a href="http://localhost/feed2"></a>
           <a href="feed3"></a>
           <a href="/feed4"></a>
           <a href="http://localhost/feed.5.xml"></a>
           <a href="http://localhost/feed.6.rss"></a>
           <a href="http://localhost/feed.7.atom"></a>
           <a href="http://localhost/feed.8.rdf"></a>
           <a href="http://localhost/feed.9.feed"></a>
           <a href="http://localhost/feed.10.php"></a>
           <a href="http://localhost/feed.11.asp"></a>
           <a href="http://localhost/feed.12.aspx"></a>
           <a href="http://localhost/feed.13.json"></a>
           <a href="http://localhost/feed.14.cgi"></a>
         </body>
        </html>
        """

        intro_context = Context(
            raw_url=UnknownUrl("http://localhost/test/xxx"),
            url=str_to_absolute_url("http://localhost/test/xxx"),
            content=html,
        )

        context, result = await _discover_create_soup(intro_context)

        new_context, result = await _discover_extract_feeds_from_anchors(context)

        expected_links = {
            AbsoluteUrl("http://localhost/feed2"),
            AbsoluteUrl("http://localhost/test/feed3"),
            AbsoluteUrl("http://localhost/feed4"),
            AbsoluteUrl("http://localhost/feed.5.xml"),
            AbsoluteUrl("http://localhost/feed.6.rss"),
            AbsoluteUrl("http://localhost/feed.7.atom"),
            AbsoluteUrl("http://localhost/feed.8.rdf"),
            AbsoluteUrl("http://localhost/feed.9.feed"),
            AbsoluteUrl("http://localhost/feed.10.php"),
            AbsoluteUrl("http://localhost/feed.11.asp"),
            AbsoluteUrl("http://localhost/feed.12.aspx"),
            AbsoluteUrl("http://localhost/feed.13.json"),
            AbsoluteUrl("http://localhost/feed.14.cgi"),
        }

        assert new_context == context.replace(candidate_urls=expected_links)
        assert result is None
