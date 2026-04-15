import pytest

from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import youtube
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

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == entry.model_copy(
            update={
                "body": (
                    '<p>Watch <a href="https://www.youtube.com/watch?v=abc">this video</a></p>\n'
                    "<ul>\n<li><strong>First</strong></li>\n<li>Second</li>\n</ul>"
                )
            }
        )

    def test_renders_bare_url_as_link(self, plugin: youtube.Plugin) -> None:
        entry = p_make.fake_entry_info(body="Watch https://www.youtube.com/watch?v=abc")

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == entry.model_copy(
            update={"body": '<p>Watch <a href="https://www.youtube.com/watch?v=abc">https://www.youtube.com/watch?v=abc</a></p>'}
        )
