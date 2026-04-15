import pytest

from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import youtube
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers.tests import make as p_make


@pytest.fixture  # type: ignore
def plugin() -> youtube.Plugin:
    return youtube.construct()


class TestDiscoverFeedUrls:
    @pytest.mark.asyncio
    async def test_returns_context_without_changes(self, plugin: youtube.Plugin) -> None:
        context = fd_make.context("https://www.youtube.com/@feedsfun/videos")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None


class TestPostprocessEntry:
    def test_renders_markdown_body_to_html(self, plugin: youtube.Plugin) -> None:
        entry = p_make.fake_entry_info(
            body="Watch [this video](https://www.youtube.com/watch?v=abc)\n\n- **First**\n- Second"
        )
        expected_body = (
            '<p>Watch <a href="https://www.youtube.com/watch?v=abc">this video</a></p>\n'
            "<ul>\n<li><strong>First</strong></li>\n<li>Second</li>\n</ul>"
        )
        expected_update: dict[str, object] = {"body": expected_body}

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == entry.replace(**expected_update)

    def test_renders_bare_url_as_link(self, plugin: youtube.Plugin) -> None:
        entry = p_make.fake_entry_info(body="Watch https://www.youtube.com/watch?v=abc")
        expected_body = (
            '<p>Watch <a href="https://www.youtube.com/watch?v=abc">' "https://www.youtube.com/watch?v=abc</a></p>"
        )
        expected_update: dict[str, object] = {"body": expected_body}

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == entry.replace(**expected_update)

    @pytest.mark.parametrize(
        ("url", "youtube_id"),
        [
            ("https://www.youtube.com/watch?v=M7lc1UVf-VE", "M7lc1UVf-VE"),
            ("https://youtu.be/M7lc1UVf-VE?t=42", "M7lc1UVf-VE"),
            ("https://www.youtube.com/embed/M7lc1UVf-VE", "M7lc1UVf-VE"),
            ("https://www.youtube.com/v/TWti2_bVsNM?version=3", "TWti2_bVsNM"),
            ("https://www.youtube.com/e/M7lc1UVf-VE", "M7lc1UVf-VE"),
            ("https://www.youtube.com/shorts/M7lc1UVf-VE", "M7lc1UVf-VE"),
            ("https://www.youtube.com/live/M7lc1UVf-VE", "M7lc1UVf-VE"),
            ("https://www.youtube-nocookie.com/embed/M7lc1UVf-VE?start=30", "M7lc1UVf-VE"),
            (
                "https://www.youtube.com/attribution_link?u=%2Fwatch%3Fv%3DM7lc1UVf-VE%26feature%3Dshare",
                "M7lc1UVf-VE",
            ),
        ],
    )
    def test_stores_youtube_id_in_video_reference_extra(
        self, plugin: youtube.Plugin, url: str, youtube_id: str
    ) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.video,
            url=str_to_absolute_url(url),
            extra={"source": "youtube"},
        )
        entry = p_make.fake_entry_info(body="Video", references=[reference])

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references[0] == reference.replace(
            extra={"source": "youtube", "youtube_id": youtube_id}
        )

    def test_does_not_store_youtube_id_for_non_youtube_video_reference(self, plugin: youtube.Plugin) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.video,
            url=str_to_absolute_url("https://example.com/video.mp4"),
        )
        entry = p_make.fake_entry_info(body="Video", references=[reference])

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references[0] == reference
