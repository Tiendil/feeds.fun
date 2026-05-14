import pytest

from ffun.domain.entities import FeedUrl
from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import reddit
from ffun.integrations.plugins.reddit import (
    _build_reddit_video_reference,
    _extract_reddit_video_link_from_first_visible_paragraph,
    _rewrite_preview_image_reference,
    _unwrap_body_with_image_table,
)
from ffun.library.entities import Reference, ReferenceKind
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
            kind=ReferenceKind.image,
            url=str_to_absolute_url(preview_url),
            title="Just got my dream camera, the A7V.",
        )
        page_reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url(
                "https://www.reddit.com/r/SonyAlpha/comments/1smrdat/just_got_my_dream_camera_the_a7v/"
            ),
        )
        entry = p_make.fake_entry_info(references=[image_reference, page_reference])

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references == [
            _rewrite_preview_image_reference(image_reference),
            _rewrite_preview_image_reference(page_reference),
        ]

    def test_rewrites_body_via_helper(self, plugin: reddit.Plugin) -> None:
        body = (
            '<table><tr><td><a href="https://www.reddit.com/r/SonyAlpha/comments/1smrdat">'
            '<img src="https://preview.redd.it/azke0yigvgvg1.jpg?width=140&height=140"></a></td>'
            '<td><div class="md"><p>Actual body.</p></div></td></tr></table>'
        )
        entry = p_make.fake_entry_info(body=body)

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.body == _unwrap_body_with_image_table(body)

    def test_extracts_first_visible_reddit_video_link_as_reference(self, plugin: reddit.Plugin) -> None:
        body = (
            '<!-- SC_OFF --><div class="md">'
            '<p><a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">'
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"
            "</a></p>"
            "<p>Hi everyone!</p>"
            "</div><!-- SC_ON --> "
            '<a href="https://www.reddit.com/user/United-Metal4470">/u/United-Metal4470</a>'
        )
        entry = p_make.fake_entry_info(body=body)

        processed_entry = plugin.postprocess_entry(entry)

        assert "n0k50i6mop0h1/player" not in processed_entry.body
        assert "Hi everyone!" in processed_entry.body
        assert processed_entry.references == [
            Reference(
                kind=ReferenceKind.video,
                url=str_to_absolute_url("https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"),
            )
        ]

    def test_keeps_reddit_video_link_when_it_is_not_first_visible_post_element(self, plugin: reddit.Plugin) -> None:
        body = (
            '<div class="md">'
            "<p>Hi everyone!</p>"
            '<p><a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">'
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"
            "</a></p>"
            "</div>"
        )
        entry = p_make.fake_entry_info(body=body)

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.body == body
        assert processed_entry.references == []

    def test_does_not_duplicate_extracted_reddit_video_reference(self, plugin: reddit.Plugin) -> None:
        video_reference = Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url("https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"),
        )
        body = (
            '<div class="md">'
            '<p><a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">'
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"
            "</a></p>"
            "<p>Hi everyone!</p>"
            "</div>"
        )
        entry = p_make.fake_entry_info(body=body, references=[video_reference])

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references == [video_reference]


class TestBuildRedditVideoReference:
    @pytest.mark.parametrize(
        "url",
        [
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player",
            "https://www.reddit.com/link/1tb297b/video/n0k50i6mop0h1/player",
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player/",
        ],
    )
    def test_builds_reference(self, url: str) -> None:
        assert _build_reddit_video_reference(url) == Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url(url),
        )

    @pytest.mark.parametrize(
        "url",
        [
            "http://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player",
            "https://old.reddit.com/link/1tb297b/video/n0k50i6mop0h1/player",
            "https://reddit.com/link/1tb297b/comments/n0k50i6mop0h1/player",
            "https://reddit.com/r/alife/comments/1tb297b/i_built_a_virtual_civilization_run_entirely_by/",
            "not-a-url",
        ],
    )
    def test_returns_none_for_unsupported_url(self, url: str) -> None:
        assert _build_reddit_video_reference(url) is None


class TestExtractRedditVideoLinkFromFirstVisibleParagraph:
    def test_extracts_reference_and_removes_first_video_paragraph(self) -> None:
        body = (
            '<!-- SC_OFF --><div class="md">'
            '<p><a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">'
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"
            "</a></p>"
            "<p>Hi everyone!</p>"
            "</div><!-- SC_ON --> "
            '<a href="https://www.reddit.com/user/United-Metal4470">/u/United-Metal4470</a>'
        )

        body, reference = _extract_reddit_video_link_from_first_visible_paragraph(body)

        assert "n0k50i6mop0h1/player" not in body
        assert "Hi everyone!" in body
        assert 'href="https://www.reddit.com/user/United-Metal4470"' in body
        assert reference == Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url("https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"),
        )

    def test_keeps_body_without_reddit_post_container(self) -> None:
        body = (
            '<p><a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">'
            "https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player"
            "</a></p>"
        )

        processed_body, reference = _extract_reddit_video_link_from_first_visible_paragraph(body)

        assert processed_body == body
        assert reference is None

    def test_keeps_body_when_first_visible_element_is_not_paragraph(self) -> None:
        body = (
            '<div class="md">'
            '<div><a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">video</a></div>'
            "</div>"
        )

        processed_body, reference = _extract_reddit_video_link_from_first_visible_paragraph(body)

        assert processed_body == body
        assert reference is None

    def test_keeps_body_when_first_paragraph_contains_extra_text(self) -> None:
        body = (
            '<div class="md">'
            '<p>Watch <a href="https://reddit.com/link/1tb297b/video/n0k50i6mop0h1/player">video</a></p>'
            "</div>"
        )

        processed_body, reference = _extract_reddit_video_link_from_first_visible_paragraph(body)

        assert processed_body == body
        assert reference is None

    def test_keeps_body_when_first_paragraph_link_is_not_reddit_video(self) -> None:
        body = '<div class="md"><p><a href="https://example.com/video">video</a></p></div>'

        processed_body, reference = _extract_reddit_video_link_from_first_visible_paragraph(body)

        assert processed_body == body
        assert reference is None


class TestRewritePreviewImageReference:
    def test_rewrites_preview_reddit_image_reference_to_i_reddit(self) -> None:
        preview_url = (
            "https://preview.redd.it/azke0yigvgvg1.jpg"
            "?width=140&height=140&crop=1:1,smart&auto=webp&s=99284d1e12e9bb76138e5368fa0cabb9e0f11b17"
        )
        reference = Reference(
            kind=ReferenceKind.image,
            url=str_to_absolute_url(preview_url),
            title="Just got my dream camera, the A7V.",
        )

        rewritten_reference = _rewrite_preview_image_reference(reference)

        assert rewritten_reference == reference.replace(url=str_to_absolute_url("https://i.redd.it/azke0yigvgvg1.jpg"))

    def test_keeps_non_preview_image_reference_unchanged(self) -> None:
        reference = Reference(
            kind=ReferenceKind.image,
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
            kind=ReferenceKind.page,
            url=str_to_absolute_url(preview_url),
        )

        rewritten_reference = _rewrite_preview_image_reference(reference)

        assert rewritten_reference == reference


class TestUnwrapBodyWithImageTable:
    def test_extracts_content_of_second_td_for_reddit_image_table(self) -> None:
        body = (
            '<table> <tbody><tr><td> <a href="https://www.reddit.com/r/SonyAlpha/comments/1smrdat/">'
            '<img title="Just got my dream camera, the A7V." '
            'src="https://preview.redd.it/azke0yigvgvg1.jpg'
            "?width=140&height=140&crop=1:1,smart&auto=webp"
            '&s=99284d1e12e9bb76138e5368fa0cabb9e0f11b17" '
            'alt="Just got my dream camera, the A7V."> </a> </td><td> <div class="md">'
            "<p>Started in 2020 with a borrowed A7II, mostly doing LEGO photography.</p>"
            "<p>Still learning, but excited for the journey.</p>"
            '</div> submitted by <a href="https://www.reddit.com/user/deadfiesta">/u/deadfiesta</a> '
            '<br><span><a href="https://www.reddit.com/gallery/1smrdat">[link]</a></span> '
            '<span><a href="https://www.reddit.com/r/SonyAlpha/comments/1smrdat/">[comments]</a></span> '
            "</td></tr></tbody></table>"
        )

        unwrapped_body = _unwrap_body_with_image_table(body)

        assert "Started in 2020 with a borrowed A7II" in unwrapped_body
        assert 'href="https://www.reddit.com/user/deadfiesta"' in unwrapped_body
        assert "<table>" not in unwrapped_body
        assert "<td>" not in unwrapped_body
        assert 'src="https://preview.redd.it/azke0yigvgvg1.jpg' not in unwrapped_body

    def test_keeps_body_without_top_level_table_unchanged(self) -> None:
        body = '<div class="md"><p>Regular reddit text body.</p></div>'

        assert _unwrap_body_with_image_table(body) == body

    def test_keeps_table_without_image_in_first_td_unchanged(self) -> None:
        body = (
            "<table><tr><td><p>Not an image cell.</p></td>"
            '<td><div class="md"><p>Actual body.</p></div></td></tr></table>'
        )

        assert _unwrap_body_with_image_table(body) == body

    def test_keeps_table_with_more_than_two_tds_unchanged(self) -> None:
        body = (
            '<table><tr><td><img src="https://preview.redd.it/example.jpg"></td>'
            "<td><p>Body.</p></td><td><p>Extra.</p></td></tr></table>"
        )

        assert _unwrap_body_with_image_table(body) == body
