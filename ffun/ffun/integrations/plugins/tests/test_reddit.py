import pytest

from ffun.domain.entities import FeedUrl
from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import reddit
from ffun.integrations.plugins.reddit import _rewrite_preview_image_reference
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers.tests import make as p_make


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


class TestPostprocessEntry:
    def test_rewrites_all_references_via_helper(self, plugin: reddit.Plugin) -> None:
        preview_url = (
            "https://preview.redd.it/azke0yigvgvg1.jpg"
            "?width=140&height=140&crop=1:1,smart&auto=webp&s=99284d1e12e9bb76138e5368fa0cabb9e0f11b17"
        )
        image_reference = Reference(
            semantics=ReferenceSemantics.image,
            url=str_to_absolute_url(preview_url),
            title="Just got my dream camera, the A7V.",
        )
        page_reference = Reference(
            semantics=ReferenceSemantics.page,
            url=str_to_absolute_url("https://www.reddit.com/r/SonyAlpha/comments/1smrdat/just_got_my_dream_camera_the_a7v/"),
        )
        entry = p_make.fake_entry_info(references=[image_reference, page_reference])

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references == [
            _rewrite_preview_image_reference(image_reference),
            _rewrite_preview_image_reference(page_reference),
        ]


class TestRewritePreviewImageReference:
    def test_rewrites_preview_reddit_image_reference_to_i_reddit(self) -> None:
        preview_url = (
            "https://preview.redd.it/azke0yigvgvg1.jpg"
            "?width=140&height=140&crop=1:1,smart&auto=webp&s=99284d1e12e9bb76138e5368fa0cabb9e0f11b17"
        )
        reference = Reference(
            semantics=ReferenceSemantics.image,
            url=str_to_absolute_url(preview_url),
            title="Just got my dream camera, the A7V.",
        )

        rewritten_reference = _rewrite_preview_image_reference(reference)

        assert rewritten_reference == reference.replace(url=str_to_absolute_url("https://i.redd.it/azke0yigvgvg1.jpg"))

    def test_keeps_non_preview_image_reference_unchanged(self) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.image,
            url=str_to_absolute_url("https://i.redd.it/oabvdva50gvg1.jpeg"),
        )

        rewritten_reference = _rewrite_preview_image_reference(reference)

        assert rewritten_reference == reference

    def test_keeps_non_image_preview_reference_unchanged(self) -> None:
        preview_url = (
            "https://preview.redd.it/azke0yigvgvg1.jpg"
            "?width=140&height=140&crop=1:1,smart&auto=webp&s=99284d1e12e9bb76138e5368fa0cabb9e0f11b17"
        )
        reference = Reference(
            semantics=ReferenceSemantics.page,
            url=str_to_absolute_url(preview_url),
        )

        rewritten_reference = _rewrite_preview_image_reference(reference)

        assert rewritten_reference == reference
