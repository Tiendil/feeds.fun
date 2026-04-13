import pytest

from ffun.domain.entities import FeedUrl
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import reddit


@pytest.fixture  # type: ignore
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
