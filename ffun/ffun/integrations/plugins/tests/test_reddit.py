
from typing import TypedDict, Unpack

import httpx
import pytest
from pytest_mock import MockerFixture
from respx.router import MockRouter

from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.domain.urls import str_to_feed_url, url_to_host
from ffun.feeds_discoverer.domain import (
    _VISITED_URLS,
    _discover_adjust_url,
    _discover_check_candidate_links,
    _discover_check_parent_urls,
    _discover_create_soup,
    _discover_extract_feed_info,
    _discover_extract_feeds_for_plugins,
    _discover_extract_feeds_from_anchors,
    _discover_extract_feeds_from_links,
    _discover_load_url,
    _discover_stop_recursion,
    _discoverers,
    discover,
    visited_cache,
)
from ffun.feeds_discoverer.entities import Context, Discoverer, Result, Status
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import reddit


@pytest.fixture
def plugin() -> reddit.Plugin:
    return reddit.construct()


class TestDiscoverFeedUrls:

    @pytest.mark.asyncio
    async def test_not_reddit(self, plugin: reddit.Plugin) -> None:
        context = fd_make.context("http://example.com/test")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_old_reditt(self, plugin: reddit.Plugin) -> None:
        context = fd_make.context(
            "https://old.reddit.com/r/feedsfun/",
        )

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.parametrize(
        "url,expected_url",
        [
            ("https://www.reddit.com/r/feedsfun/", "https://www.reddit.com/r/feedsfun/.rss"),
            ("https://www.reddit.com/r/feedsfun/?sd=x", "https://www.reddit.com/r/feedsfun/.rss"),
            ("https://www.reddit.com/r/feedsfun", "https://www.reddit.com/r/feedsfun/.rss"),
            ("https://reddit.com/r/feedsfun/", "https://reddit.com/r/feedsfun/.rss"),
            ("https://reddit.com/r/feedsfun", "https://reddit.com/r/feedsfun/.rss"),
            (
                "https://www.reddit.com/r/feedsfun/comments/1ho4k84/version_116_released_meet_enhanced_rules_creation/",  # noqa
                "https://www.reddit.com/r/feedsfun/.rss",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_new_reddit(self, plugin: reddit.Plugin, url: str, expected_url: FeedUrl) -> None:
        context = context = fd_make.context(url)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(candidate_urls={expected_url})
        assert result is None

    @pytest.mark.asyncio
    async def test_already_reddit_rss_url(self, plugin: reddit.Plugin) -> None:
        context = context = fd_make.context("https://www.reddit.com/r/feedsfun/.rss")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None
