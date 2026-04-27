import pytest
from pytest_mock import MockerFixture

from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import youtube
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers.tests import make as p_make


@pytest.fixture  # type: ignore
def plugin() -> youtube.Plugin:
    return youtube.construct()


class TestConstruct:
    def test_uses_default_values(self) -> None:
        plugin = youtube.construct()

        assert plugin._channel_feed_url == youtube.DEFAULT_CHANNEL_FEED_URL

    def test_uses_passed_values(self) -> None:
        plugin = youtube.construct(channel_feed_url="https://example.com/{channel_id}.xml")

        assert plugin._channel_feed_url == "https://example.com/{channel_id}.xml"


class TestAutolinkBareUrls:
    def test_wraps_bare_urls_but_keeps_trailing_punctuation_outside_link(self) -> None:
        text = "Watch https://www.youtube.com/watch?v=abc, then reply."

        assert youtube._autolink_bare_urls(text) == "Watch <https://www.youtube.com/watch?v=abc>, then reply."


class TestIsYoutubeHost:
    @pytest.mark.parametrize(
        ("hostname", "expected"),
        [
            ("youtube.com", True),
            ("www.youtube.com", True),
            ("m.youtube.com", True),
            ("youtu.be", True),
            ("www.youtube-nocookie.com", True),
            ("example.com", False),
        ],
    )
    def test_detects_supported_hosts(self, hostname: str, expected: bool) -> None:
        assert youtube._is_youtube_host(hostname) is expected


class TestIsYoutubeFeedUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890123456789012", True),
            ("https://www.youtube.com/watch?v=abc", False),
        ],
    )
    def test_detects_feed_urls(self, url: str, expected: bool) -> None:
        assert youtube._is_youtube_feed_url(url) is expected


class TestDetectYoutubePageKind:
    @pytest.mark.parametrize(
        ("url", "expected_kind"),
        [
            ("https://www.youtube.com/watch?v=abc", youtube.YouTubePageKind.video),
            ("https://youtu.be/M7lc1UVf-VE", youtube.YouTubePageKind.video),
            ("https://www.youtube.com/embed/M7lc1UVf-VE", youtube.YouTubePageKind.video),
            ("https://www.youtube.com/@feedsfun/videos", youtube.YouTubePageKind.channel),
            ("https://www.youtube.com/channel/UC1234567890123456789012", youtube.YouTubePageKind.channel),
            (
                "https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890123456789012",
                youtube.YouTubePageKind.feed,
            ),
            ("https://www.youtube.com/playlist?list=abc", youtube.YouTubePageKind.other),
            ("https://example.com/watch?v=abc", youtube.YouTubePageKind.non_youtube),
        ],
    )
    def test_detects_page_kind(self, url: str, expected_kind: youtube.YouTubePageKind) -> None:
        assert youtube._detect_youtube_page_kind(url) == expected_kind


class TestExtractChannelIdsWithPatterns:
    def test_extracts_ids_for_passed_patterns(self) -> None:
        content = """
            <script>
                {
                    "videoDetails":{"videoId":"abc","channelId":"UC1234567890123456789012"},
                    "externalChannelId":"UCabcdefghijklmnopqrstuv"
                }
            </script>
        """

        assert youtube._extract_channel_ids_with_patterns(content, youtube._YOUTUBE_VIDEO_PAGE_CHANNEL_PATTERNS) == {
            "UC1234567890123456789012",
            "UCabcdefghijklmnopqrstuv",
        }


class TestExtractChannelIdsFromVideoPageContent:
    def test_extracts_only_explicit_owner_channel_ids(self) -> None:
        content = """
            <script>
                {
                    "videoDetails":{"videoId":"abc","channelId":"UC1234567890123456789012"},
                    "externalChannelId":"UC1234567890123456789012",
                    "channelMetadataRenderer":{"externalId":"UCabcdefghijklmnopqrstuv"},
                    "secondaryResults":[
                        {"compactVideoRenderer":{"browseId":"UCrelated0000000000000000"}},
                        {"compactVideoRenderer":{"browseId":"UCmoreRelated0000000000000"}}
                    ]
                }
            </script>
        """

        assert youtube._extract_channel_ids_from_video_page_content(content) == {
            "UC1234567890123456789012",
        }


class TestExtractChannelIdsFromChannelPageContent:
    def test_extracts_channel_id_from_channel_metadata(self) -> None:
        content = """
            <script>
                {
                    "channelMetadataRenderer":{"externalId":"UCabcdefghijklmnopqrstuv"},
                    "secondaryResults":[
                        {"compactVideoRenderer":{"browseId":"UCrelated0000000000000000"}}
                    ]
                }
            </script>
        """

        assert youtube._extract_channel_ids_from_channel_page_content(content) == {
            "UCabcdefghijklmnopqrstuv",
        }


class TestBuildFeedUrlsForChannelIds:
    def test_builds_feed_urls_from_template(self) -> None:
        assert youtube._build_feed_urls_for_channel_ids(
            {"UC1234567890123456789012"},
            "https://example.com/channels/{channel_id}.xml",
        ) == {str_to_absolute_url("https://example.com/channels/UC1234567890123456789012.xml")}


class TestNormalizeNestedYoutubeUrl:
    def test_normalizes_relative_url_against_youtube_root(self) -> None:
        assert youtube._normalize_nested_youtube_url("/watch?v=M7lc1UVf-VE") == str_to_absolute_url(
            "https://www.youtube.com/watch?v=M7lc1UVf-VE"
        )

    def test_normalizes_absolute_url(self) -> None:
        assert youtube._normalize_nested_youtube_url("https://www.youtube.com/watch?v=M7lc1UVf-VE") == (
            str_to_absolute_url("https://www.youtube.com/watch?v=M7lc1UVf-VE")
        )

    def test_returns_none_for_invalid_url(self) -> None:
        assert youtube._normalize_nested_youtube_url("not a url") is None


class TestDiscoverFeedUrls:
    @pytest.mark.asyncio
    async def test_returns_context_without_changes_for_non_youtube_page(self, plugin: youtube.Plugin) -> None:
        context = fd_make.context("https://example.com/watch?v=abc")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_loads_video_page_and_constructs_feed_urls(
        self, mocker: MockerFixture, plugin: youtube.Plugin
    ) -> None:
        context = fd_make.context("https://www.youtube.com/watch?v=abc")

        async def fake_load_decoded_content(url: object, headers: object = None) -> str | None:
            assert url == "https://www.youtube.com/watch?v=abc"
            assert headers == youtube._YOUTUBE_DISCOVERY_HEADERS
            return """
                <html>
                    <script>
                        var ytInitialData = {
                            "videoDetails": {"channelId": "UCabcdefghijklmnopqrstuv"},
                            "externalChannelId": "UC1234567890123456789012",
                            "secondaryResults": [
                                {"compactVideoRenderer": {"browseId": "UCrelated0000000000000000"}}
                            ]
                        };
                    </script>
                </html>
            """

        mocker.patch.object(youtube.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890123456789012",
                "https://www.youtube.com/feeds/videos.xml?channel_id=UCabcdefghijklmnopqrstuv",
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_loads_channel_page_and_constructs_feed_urls(
        self, mocker: MockerFixture, plugin: youtube.Plugin
    ) -> None:
        context = fd_make.context("https://www.youtube.com/@feedsfun/videos")

        async def fake_load_decoded_content(url: object, headers: object = None) -> str | None:
            assert url == "https://www.youtube.com/@feedsfun/videos"
            assert headers == youtube._YOUTUBE_DISCOVERY_HEADERS
            return (
                '<script>{"channelMetadataRenderer":{"externalId":"UC1234567890123456789012"},'
                '"browseId":"UCrelated0000000000000000"}</script>'
            )

        mocker.patch.object(youtube.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890123456789012",
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_loads_channel_handle_page_and_constructs_feed_urls(
        self, mocker: MockerFixture, plugin: youtube.Plugin
    ) -> None:
        context = fd_make.context("https://www.youtube.com/@CainOnGames")

        async def fake_load_decoded_content(url: object, headers: object = None) -> str | None:
            assert url == "https://www.youtube.com/@CainOnGames"
            assert headers == youtube._YOUTUBE_DISCOVERY_HEADERS
            return '<script>{"channelMetadataRenderer":{"externalId":"UCTAfm-YD2M9xzvbYvRc5ttA"}}</script>'

        mocker.patch.object(youtube.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://www.youtube.com/feeds/videos.xml?channel_id=UCTAfm-YD2M9xzvbYvRc5ttA",
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_keeps_existing_candidate_urls(self, mocker: MockerFixture, plugin: youtube.Plugin) -> None:
        context = fd_make.context(
            "https://www.youtube.com/watch?v=abc",
            candidate_urls={str_to_absolute_url("https://existing.example.com/feed.xml")},
        )

        async def fake_load_decoded_content(url: object, headers: object = None) -> str | None:
            assert url == "https://www.youtube.com/watch?v=abc"
            assert headers == youtube._YOUTUBE_DISCOVERY_HEADERS
            return (
                '<script>{"videoDetails":{"channelId":"UC1234567890123456789012"},'
                '"browseId":"UCrelated0000000000000000"}</script>'
            )

        mocker.patch.object(youtube.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                str_to_absolute_url("https://existing.example.com/feed.xml"),
                "https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890123456789012",
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_configured_channel_feed_url(self, mocker: MockerFixture) -> None:
        plugin = youtube.construct(channel_feed_url="https://example.com/channels/{channel_id}.xml")
        context = fd_make.context("https://www.youtube.com/watch?v=abc")

        async def fake_load_decoded_content(url: object, headers: object = None) -> str | None:
            assert url == "https://www.youtube.com/watch?v=abc"
            assert headers == youtube._YOUTUBE_DISCOVERY_HEADERS
            return (
                '<script>{"videoDetails":{"channelId":"UC1234567890123456789012"},'
                '"browseId":"UCrelated0000000000000000"}</script>'
            )

        mocker.patch.object(youtube.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://example.com/channels/UC1234567890123456789012.xml",
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_existing_youtube_feed_url(self, plugin: youtube.Plugin) -> None:
        context = fd_make.context("https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890123456789012")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None


class TestExtractYoutubeVideoIdFromUrl:
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
    def test_extracts_video_id(self, url: str, youtube_id: str) -> None:
        assert youtube._extract_youtube_video_id_from_url(str_to_absolute_url(url)) == youtube_id

    def test_returns_none_for_non_youtube_url(self) -> None:
        assert youtube._extract_youtube_video_id_from_url(str_to_absolute_url("https://example.com/video.mp4")) is None


class TestPostprocessReference:
    def test_stores_youtube_id_in_video_reference_extra(self) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.video,
            url=str_to_absolute_url("https://www.youtube.com/watch?v=M7lc1UVf-VE"),
            extra={"source": "youtube"},
        )

        assert youtube._postprocess_reference(reference) == reference.replace(
            extra={"source": "youtube", "youtube_id": "M7lc1UVf-VE"}
        )

    def test_keeps_non_youtube_video_reference(self) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.video,
            url=str_to_absolute_url("https://example.com/video.mp4"),
        )

        assert youtube._postprocess_reference(reference) == reference

    def test_keeps_non_video_reference(self) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.page,
            url=str_to_absolute_url("https://www.youtube.com/watch?v=M7lc1UVf-VE"),
        )

        assert youtube._postprocess_reference(reference) == reference


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

    def test_uses_postprocessed_references(self, plugin: youtube.Plugin) -> None:
        reference = Reference(
            semantics=ReferenceSemantics.video,
            url=str_to_absolute_url("https://example.com/video.mp4"),
        )
        entry = p_make.fake_entry_info(body="Video", references=[reference])

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references[0] == reference
