import pytest

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
