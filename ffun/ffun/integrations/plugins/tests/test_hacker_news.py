import pytest

from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import hacker_news
from ffun.integrations.plugins.hacker_news import _swap_link_and_comments
from ffun.library.entities import Reference, ReferenceKind
from ffun.parsers.tests import make as p_make


@pytest.fixture  # type: ignore
def plugin() -> hacker_news.Plugin:
    return hacker_news.construct()


class TestDiscoverFeedUrls:
    @pytest.mark.asyncio
    async def test_returns_context_without_changes(self, plugin: hacker_news.Plugin) -> None:
        context = fd_make.context("https://news.ycombinator.com/rss")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None


class TestSwapLinkAndComments:
    def test_swaps_original_article_link_with_comments_link(self) -> None:
        article_url = str_to_absolute_url("https://example.com/article")
        comments_reference = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://news.ycombinator.com/item?id=1"),
            title="Comments",
        )
        author_reference = Reference(
            kind=ReferenceKind.author,
            url=str_to_absolute_url("https://news.ycombinator.com/user?id=tiendil"),
            title="tiendil",
        )
        entry = p_make.fake_entry_info(
            body="<p>Discussion body</p>",
            external_url=article_url,
            references=[comments_reference, author_reference],
        )

        processed_entry = _swap_link_and_comments(entry)

        assert processed_entry == entry.replace(
            external_url=comments_reference.url,
            references=[
                comments_reference,
                author_reference,
                Reference(
                    kind=ReferenceKind.page,
                    url=article_url,
                    title="Original article",
                ),
            ],
        )

    def test_keeps_entry_when_primary_link_is_already_hacker_news(self) -> None:
        comments_reference = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://news.ycombinator.com/item?id=1"),
            title="Comments",
        )
        entry = p_make.fake_entry_info(
            external_url=str_to_absolute_url("https://news.ycombinator.com/item?id=1"),
            references=[comments_reference],
        )

        assert _swap_link_and_comments(entry) == entry

    def test_keeps_entry_when_comments_reference_is_missing(self) -> None:
        article_url = str_to_absolute_url("https://example.com/article")
        entry = p_make.fake_entry_info(
            external_url=article_url,
            references=[
                Reference(
                    kind=ReferenceKind.author,
                    url=str_to_absolute_url("https://news.ycombinator.com/user?id=tiendil"),
                )
            ],
        )

        assert _swap_link_and_comments(entry) == entry

    def test_keeps_entry_when_primary_link_host_is_configured_as_original(self) -> None:
        comments_reference = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://news.ycombinator.com/item?id=1"),
            title="Comments",
        )
        entry = p_make.fake_entry_info(
            external_url=str_to_absolute_url("https://example.com/article"),
            references=[comments_reference],
        )

        assert _swap_link_and_comments(entry, ("news.ycombinator.com", "example.com")) == entry


class TestPostprocessEntry:
    def test_uses_swap_link_and_comments_helper(self, plugin: hacker_news.Plugin) -> None:
        article_url = str_to_absolute_url("https://example.com/article")
        comments_reference = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://news.ycombinator.com/item?id=1"),
            title="Comments",
        )
        entry = p_make.fake_entry_info(
            body="<p>Discussion body</p>",
            external_url=article_url,
            references=[comments_reference],
        )

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == _swap_link_and_comments(entry)

    def test_uses_configured_original_hosts(self) -> None:
        plugin = hacker_news.construct(original_hosts=["news.ycombinator.com", "example.com"])
        comments_reference = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://news.ycombinator.com/item?id=1"),
            title="Comments",
        )
        entry = p_make.fake_entry_info(
            external_url=str_to_absolute_url("https://example.com/article"),
            references=[comments_reference],
        )

        assert plugin.postprocess_entry(entry) == entry
