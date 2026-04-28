import datetime
import io
from types import SimpleNamespace
from typing import Mapping

import pytest
from pytest_mock import MockerFixture

from ffun.core import json, utils
from ffun.core.tests.helpers import assert_logs, capture_logs
from ffun.domain.entities import AbsoluteUrl, FeedUrl, SourceUid, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url, url_to_source_uid
from ffun.integrations.tests.helpers import FakeIntegration
from ffun.library.entities import Reference, ReferenceKind
from ffun.parsers import errors
from ffun.parsers import feed as p_feed
from ffun.parsers.entities import EntryInfo, FeedInfo
from ffun.parsers.feed import (
    _create_reference,
    _extract_author_reference,
    _extract_body,
    _extract_comments_reference,
    _extract_content,
    _extract_enclosure_reference,
    _extract_external_id,
    _extract_external_url,
    _extract_link_reference,
    _extract_media_content_reference,
    _extract_media_reference,
    _extract_media_thumbnail_reference,
    _extract_published_at,
    _extract_references,
    _extract_references_raw,
    _media_type_to_kind,
    _merge_references_list,
    _parse_stream,
    _parse_tags,
    _reference_kind_from_link,
    _should_skip,
    parse_entry,
    parse_feed,
    parse_into_feedparser,
)
from ffun.parsers.tests.helpers import feeds_fixtures_directory, feeds_fixtures_names


@pytest.fixture  # type: ignore
def feed_url() -> FeedUrl:
    normalized_url = normalize_classic_unknown_url(UnknownUrl("https://example.com/feed/"))
    assert normalized_url is not None
    return to_feed_url(normalized_url)


def _absolute_url(url: str) -> AbsoluteUrl:
    normalized_url = normalize_classic_unknown_url(UnknownUrl(url))
    assert normalized_url is not None
    return normalized_url


class TestParseTags:

    def test_empty(self) -> None:
        assert _parse_tags([]) == set()

    def test_prefers_label_and_falls_back_to_term(self) -> None:
        tags = [
            {"label": "label-1", "term": "term-1"},
            {"term": "term-2"},
            {},
        ]

        assert _parse_tags(tags) == {"label-1", "term-2"}


class TestShouldSkip:

    def test_returns_true_and_logs_when_link_is_missing(self) -> None:
        with capture_logs() as logs:
            result = _should_skip({})

        assert result is True
        assert_logs(logs, feed_does_not_has_link_field=1)

    def test_returns_false_when_link_exists(self) -> None:
        assert _should_skip({"link": "https://example.com/news"}) is False


class TestParseEntry:

    def test_parse_without_plugin(self, feed_url: FeedUrl) -> None:
        raw_entry = {
            "title": "Entry title 1",
            "link": "/2023/07/25/news-1.html",
            "published_parsed": (2023, 7, 25, 17, 15, 0, 0, 0, -1),
            "description": "Body 1",
            "author_detail": {},
            "tags": [
                {"term": "tag1"},
                {"term": "tag2"},
                {"label": "tag3"},
            ],
        }

        parsed_entry = parse_entry(raw_entry, feed_url, url_to_source_uid(feed_url))
        expected_external_url = normalize_classic_unknown_url(UnknownUrl("https://example.com/2023/07/25/news-1.html"))

        assert expected_external_url is not None

        expected_entry = EntryInfo(
            title="Entry title 1",
            body="Body 1",
            external_id="/2023/07/25/news-1.html",
            external_url=expected_external_url,
            published_at=datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc),
            external_tags={"tag1", "tag2", "tag3"},
            references=[],
        )

        assert parsed_entry == expected_entry

    def test_calls_plugin_and_returns_updated_entry(self, mocker: MockerFixture, feed_url: FeedUrl) -> None:
        raw_entry = {
            "title": "Entry title 1",
            "link": "/2023/07/25/news-1.html",
            "published_parsed": (2023, 7, 25, 17, 15, 0, 0, 0, -1),
            "description": "Body 1",
            "author_detail": {},
            "tags": [{"term": "tag1"}],
        }
        integration = FakeIntegration(["example.com", "www.example.com"], [])
        mocker.patch.object(
            p_feed.i_settings,
            "integrations",
            [integration],
        )

        parsed_entry = parse_entry(raw_entry, feed_url, url_to_source_uid(feed_url))

        assert "fake-plugin" in parsed_entry.external_tags

    def test_calls_plugin_when_source_matches_secondary_configured_source(
        self, mocker: MockerFixture, feed_url: FeedUrl
    ) -> None:
        raw_entry = {
            "title": "Entry title 1",
            "link": "/2023/07/25/news-1.html",
            "published_parsed": (2023, 7, 25, 17, 15, 0, 0, 0, -1),
            "description": "Body 1",
            "author_detail": {},
            "tags": [{"term": "tag1"}],
        }
        integration = FakeIntegration(["example.com", "www.example.com"], [])
        mocker.patch.object(
            p_feed.i_settings,
            "integrations",
            [integration],
        )

        parsed_entry = parse_entry(raw_entry, feed_url, SourceUid("www.example.com"))

        assert "fake-plugin" in parsed_entry.external_tags

    def test_raises_when_external_url_can_not_be_extracted(self, feed_url: FeedUrl) -> None:
        with pytest.raises(errors.CanNotExtractExternalUrl):
            parse_entry({"title": "Entry", "link": "mailto:test@example.com"}, feed_url, url_to_source_uid(feed_url))


class TestParseFeed:

    def test_error_in_feedparser(self, mocker: MockerFixture, feed_url: FeedUrl) -> None:
        mocker.patch("feedparser.parse", side_effect=ValueError("Test error in feedparser"))

        with capture_logs() as logs:
            feed_info = parse_feed("", feed_url, url_to_source_uid(feed_url))

        assert feed_info is None
        assert_logs(logs, error_while_parsing_feed=1)

    @pytest.mark.parametrize("raw_fixture_name", feeds_fixtures_names())
    def test_on_row_fixtures(self, raw_fixture_name: str, feed_url: FeedUrl) -> None:
        raw_fixture_path = feeds_fixtures_directory / raw_fixture_name
        expected_fixture_path = str(raw_fixture_path) + ".expected.json"

        with open(raw_fixture_path, "r", encoding="utf-8") as raw_fixture_file:
            raw_fixture = raw_fixture_file.read()

        with open(expected_fixture_path, "r", encoding="utf-8") as expected_fixture_file:
            expected_fixture = expected_fixture_file.read()

        feed_info = parse_feed(raw_fixture, feed_url, url_to_source_uid(feed_url))

        assert feed_info == FeedInfo.model_validate_json(expected_fixture)

    @pytest.mark.parametrize("raw_fixture_name", feeds_fixtures_names())
    def test_skip_entry_on_error(self, raw_fixture_name: str, mocker: MockerFixture, feed_url: FeedUrl) -> None:
        raw_fixture_path = feeds_fixtures_directory / raw_fixture_name
        expected_fixture_path = str(raw_fixture_path) + ".expected.json"

        with open(raw_fixture_path, "r", encoding="utf-8") as raw_fixture_file:
            raw_fixture = raw_fixture_file.read()

        with open(expected_fixture_path, "r", encoding="utf-8") as expected_fixture_file:
            expected_fixture = expected_fixture_file.read()

        call_number = {"calls": 0}

        def mocked_parse_entry(raw_entry: object, original_url: FeedUrl, source: SourceUid) -> EntryInfo:
            call_number["calls"] += 1

            if call_number["calls"] == 1:
                raise ValueError("Test error on entry parsing")

            return parse_entry(raw_entry, original_url, source)  # type: ignore

        mocker.patch("ffun.parsers.feed.parse_entry", side_effect=mocked_parse_entry)

        with capture_logs() as logs:
            feed_info = parse_feed(raw_fixture, feed_url, url_to_source_uid(feed_url))

        assert_logs(logs, error_while_parsing_feed_entry=1)

        # the first entry will be skipped due to the error in parsing
        parsed_expected_fixture = json.parse(expected_fixture)
        parsed_expected_fixture["entries"] = parsed_expected_fixture["entries"][1:]  # type: ignore

        assert feed_info == FeedInfo.model_validate(parsed_expected_fixture)

    def test_parse_broken_html(self, feed_url: FeedUrl) -> None:
        result = parse_feed("I'm a broken feed content", feed_url, url_to_source_uid(feed_url))
        assert result is None, "Broken HTML should return None"

        # a real example of misplaced content
        input = """\n// Copyright 2012 Google Inc. All rights reserved.\n \n (function(w,g){w[g]=w[g]||{};\n w[g].e=function(s){return eval(s);};})(window,\'google_tag_manager\');\n \n(function(){\n\nvar data = {\n"resource": {\n  "version":"29",\n  \n  "macros":[{"function":"__u","vtp_component":"HOST","vtp_enableMultiQueryKeys":false,"vtp_enableIgnoreEmptyQueryParam":false},{"function":"__v","vtp_name":"gtm.historyChangeSource","vtp_dataLayerVersion":1},{"function":"__u","vtp_component":"PATH","vtp_enableMultiQueryKeys":false,"vtp_enableIgnoreEmptyQueryParam":false},{"function":"__e"},{"function":"__v","vtp_dataLayerVersion":2,"vtp_setDefaultValue":false,"vtp_name":"originalLocation"},{"function":"__jsm","vtp_javascript":["template","(function(){return document.location.pathname+document.location.search})();"]},{"function":"__jsm","vtp_javascript":["template","(function(){var b=9;return function(a){a.set(\\"dimension\\"+b,a.get(\\"hitType\\"))}})();"]},{"function":"__gas","vtp_cookieDomain":"auto","vtp_doubleClick":false"""  # noqa: E501

        result = parse_feed(input, feed_url, url_to_source_uid(feed_url))
        assert result is None, "Broken HTML should return None"

    def test_returns_none_when_channel_has_no_version_and_no_entries(
        self, mocker: MockerFixture, feed_url: FeedUrl
    ) -> None:
        feed: Mapping[str, object] = {}
        entries: list[Mapping[str, object]] = []
        channel = SimpleNamespace(feed=feed, entries=entries, version="")
        mocker.patch("ffun.parsers.feed.parse_into_feedparser", return_value=channel)

        assert parse_feed("<feed />", feed_url, url_to_source_uid(feed_url)) is None

    def test_skips_entries_without_link(self, feed_url: FeedUrl) -> None:
        result = parse_feed(
            """
            <rss version="2.0">
              <channel>
                <title>Title</title>
                <description>Description</description>
                <item><title>Broken entry</title></item>
              </channel>
            </rss>
            """,
            feed_url,
            url_to_source_uid(feed_url),
        )

        assert result is not None
        assert result.entries == []

    def test_preserves_iframe_markup_for_frontend_sanitizer(self, feed_url: FeedUrl) -> None:
        result = parse_feed(
            """
            <rss version="2.0">
              <channel>
                <title>Title</title>
                <description>Description</description>
                <item>
                  <title>Entry</title>
                  <link>https://example.com/entry</link>
                  <description><![CDATA[
                    <p>Before</p>
                    <iframe src="https://www.youtube.com/embed/video-id"
                            width="560"
                            height="315"
                            title="Video"
                            sandbox="allow-top-navigation"></iframe>
                    <iframe src="https://www.youtube.com/embed/srcdoc-video-id"
                            srcdoc="<p>HTML</p>"
                            sandbox="allow-top-navigation"></iframe>
                    <script>alert(1)</script>
                    <p>After</p>
                  ]]></description>
                </item>
              </channel>
            </rss>
            """,
            feed_url,
            url_to_source_uid(feed_url),
        )

        assert result is not None
        assert len(result.entries) == 1
        body = result.entries[0].body

        assert "<iframe" in body
        assert 'src="https://www.youtube.com/embed/video-id"' in body
        assert 'width="560"' in body
        assert 'height="315"' in body
        assert 'title="Video"' in body
        assert 'srcdoc="' not in body
        assert 'src="https://www.youtube.com/embed/srcdoc-video-id"' in body
        assert "sandbox" not in body
        assert "<script" not in body
        assert "alert(1)" not in body


class TestExtractPublishedAt:

    def test_ok(self) -> None:
        published_parsed = (2023, 7, 25, 17, 15, 0, 0, 0, -1)
        expected_published_at = datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc)
        assert _extract_published_at({"published_parsed": published_parsed}) == expected_published_at

    def test_value_error(self) -> None:
        published_parsed = (1, 1, 1, 0, 0, 0, 0, 1, 0)
        assert (utils.now() - _extract_published_at({"published_parsed": published_parsed})).total_seconds() < 1

    def test_no_published_but_has_updated(self) -> None:
        updated_parsed = (2023, 7, 25, 17, 15, 0, 0, 0, -1)
        expected_published_at = datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc)
        assert _extract_published_at({"updated_parsed": updated_parsed}) == expected_published_at

    def test_published_priority_over_updated(self) -> None:
        published_parsed = (2023, 7, 25, 17, 15, 0, 0, 0, -1)
        updated_parsed = (2022, 1, 1, 0, 0, 0, 0, 0, -1)
        expected_published_at = datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc)
        assert (
            _extract_published_at({"published_parsed": published_parsed, "updated_parsed": updated_parsed})
            == expected_published_at
        )

    def test_returns_now_when_both_dates_are_missing(self) -> None:
        assert (utils.now() - _extract_published_at({})).total_seconds() < 1


class TestExtractContent:

    def test_returns_none_when_content_is_missing(self) -> None:
        entry: dict[str, object] = {}
        assert _extract_content(entry) is None

    def test_returns_first_value_when_single_content_item(self) -> None:
        entry: dict[str, object] = {"content": [{"value": "single"}]}
        assert _extract_content(entry) == "single"

    def test_returns_longest_value_from_multiple_content_items(self) -> None:
        entry: dict[str, object] = {
            "content": [
                {"value": "short"},
                {"value": "the-longest-value"},
                {"value": "mid"},
            ]
        }
        assert _extract_content(entry) == "the-longest-value"

    def test_keeps_first_value_when_next_value_has_equal_length(self) -> None:
        entry: dict[str, object] = {
            "content": [
                {"value": "same"},
                {"value": "size"},
            ]
        }
        assert _extract_content(entry) == "same"


class TestExtractBody:

    def test_returns_empty_string_when_description_and_content_are_missing(self) -> None:
        entry: dict[str, object] = {}
        assert _extract_body(entry) == ""

    def test_returns_content_when_description_is_missing(self) -> None:
        entry: dict[str, object] = {"content": [{"value": "content-body"}]}
        assert _extract_body(entry) == "content-body"

    def test_returns_description_when_content_is_missing(self) -> None:
        entry: dict[str, object] = {"description": "description-body"}
        assert _extract_body(entry) == "description-body"

    def test_returns_content_when_it_is_longer_or_equal_than_description(self) -> None:
        entry: dict[str, object] = {
            "description": "short",
            "content": [{"value": "content-is-longer"}],
        }
        assert _extract_body(entry) == "content-is-longer"

    def test_returns_description_when_it_is_longer_than_content(self) -> None:
        entry: dict[str, object] = {
            "description": "description-is-longer",
            "content": [{"value": "short"}],
        }
        assert _extract_body(entry) == "description-is-longer"


class TestExtractExternalId:

    def test_returns_link(self) -> None:
        assert _extract_external_id({"link": "https://example.com/news"}) == "https://example.com/news"


class TestExtractExternalUrl:

    def test_returns_adjusted_url(self, feed_url: FeedUrl) -> None:
        assert _extract_external_url({"link": "/news"}, feed_url) == "https://example.com/news"

    def test_raises_when_link_is_missing(self, feed_url: FeedUrl) -> None:
        with pytest.raises(errors.CanNotExtractExternalUrl):
            _extract_external_url({}, feed_url)

    def test_raises_when_link_is_not_valid(self, feed_url: FeedUrl) -> None:
        with pytest.raises(errors.CanNotExtractExternalUrl):
            _extract_external_url({"link": "mailto:test@example.com"}, feed_url)


class TestMediaTypeToKind:

    @pytest.mark.parametrize(
        ("media_type", "expected"),
        [
            (None, ReferenceKind.unknown),
            ("image/png", ReferenceKind.image),
            (" IMAGE/PNG ", ReferenceKind.image),
            ("audio/mpeg", ReferenceKind.audio),
            ("audio/mpeg; codecs=mp3", ReferenceKind.audio),
            ("video/mp4", ReferenceKind.video),
            (" video/mp4 ; codecs=avc1 ", ReferenceKind.video),
            ("text/html", ReferenceKind.page),
            ("text/html; charset=utf-8", ReferenceKind.page),
            ("application/xhtml+xml", ReferenceKind.page),
            ("application/x-shockwave-flash", ReferenceKind.video),
            ("application/pdf", ReferenceKind.document),
            ("text/plain", ReferenceKind.document),
            ("application/json", ReferenceKind.document),
            ("application/octet-stream", ReferenceKind.document),
            ("x-custom/thing", ReferenceKind.unknown),
        ],
    )
    def test(self, media_type: str | None, expected: ReferenceKind) -> None:
        assert _media_type_to_kind(media_type) == expected


class TestCreateReference:

    def test_returns_none_when_url_is_missing(self, feed_url: FeedUrl) -> None:
        assert _create_reference(ReferenceKind.page, None, feed_url) is None

    def test_returns_none_when_url_is_invalid(self, feed_url: FeedUrl) -> None:
        assert _create_reference(ReferenceKind.page, "mailto:test@example.com", feed_url) is None

    def test_returns_none_on_metadata_parsing_error(self, feed_url: FeedUrl) -> None:
        assert _create_reference(ReferenceKind.page, "/news", feed_url, width="bad-int") is None

    def test_creates_reference(self, feed_url: FeedUrl) -> None:
        reference = _create_reference(
            kind=ReferenceKind.video,
            url="/video",
            original_url=feed_url,
            title="Title",
            mime_type="video/mp4",
            width="640",
            height="360",
            duration="12.5",
            size="99",
            extra={"id": "video-id"},
        )

        assert reference == Reference(
            kind=ReferenceKind.video,
            url=_absolute_url("https://example.com/video"),
            title="Title",
            mime_type="video/mp4",
            width=640,
            height=360,
            duration=datetime.timedelta(seconds=12.5),
            size=99,
            extra={"id": "video-id"},
        )


class TestReferenceKindFromLink:

    def test_returns_comments_for_replies(self) -> None:
        assert _reference_kind_from_link("replies", None) == ReferenceKind.comments

    def test_prefers_media_type_when_it_is_known(self) -> None:
        assert _reference_kind_from_link("alternate", "image/png") == ReferenceKind.image

    @pytest.mark.parametrize("rel", ["alternate", "related", "via"])
    def test_returns_page_for_page_like_rels(self, rel: str) -> None:
        assert _reference_kind_from_link(rel, None) == ReferenceKind.page

    def test_returns_unknown_for_other_rels(self) -> None:
        assert _reference_kind_from_link("self", None) == ReferenceKind.unknown


class TestExtractLinkReference:

    def test_returns_none_when_href_is_missing(self, feed_url: FeedUrl) -> None:
        assert _extract_link_reference({}, feed_url) is None

    def test_returns_reference(self, feed_url: FeedUrl) -> None:
        assert _extract_link_reference(
            {"href": "/page", "rel": "alternate", "type": "text/html", "title": "Page"},
            feed_url,
        ) == Reference(
            kind=ReferenceKind.page,
            url=_absolute_url("https://example.com/page"),
            title="Page",
            mime_type="text/html",
        )


class TestExtractMediaReference:

    def test_returns_none_when_url_is_missing(self, feed_url: FeedUrl) -> None:
        assert _extract_media_reference({}, feed_url, ReferenceKind.image) is None

    def test_uses_default_kind_for_unknown_media_type(self, feed_url: FeedUrl) -> None:
        assert _extract_media_reference({"url": "/asset"}, feed_url, ReferenceKind.image) == Reference(
            kind=ReferenceKind.image,
            url=_absolute_url("https://example.com/asset"),
        )

    def test_known_media_type_overrides_default(self, feed_url: FeedUrl) -> None:
        assert _extract_media_reference(
            {"url": "/asset", "type": "video/mp4"},
            feed_url,
            ReferenceKind.image,
        ) == Reference(
            kind=ReferenceKind.video,
            url=_absolute_url("https://example.com/asset"),
            mime_type="video/mp4",
        )


class TestExtractMediaContentReference:

    def test_uses_unknown_default_kind(self, feed_url: FeedUrl) -> None:
        assert _extract_media_content_reference({"url": "/asset"}, feed_url) == Reference(
            kind=ReferenceKind.unknown,
            url=_absolute_url("https://example.com/asset"),
        )


class TestExtractMediaThumbnailReference:

    def test_uses_image_default_kind(self, feed_url: FeedUrl) -> None:
        assert _extract_media_thumbnail_reference({"url": "/image"}, feed_url) == Reference(
            kind=ReferenceKind.image,
            url=_absolute_url("https://example.com/image"),
        )


class TestExtractCommentsReference:

    def test_returns_none_when_missing(self, feed_url: FeedUrl) -> None:
        assert _extract_comments_reference(None, feed_url) is None

    def test_returns_comments_reference(self, feed_url: FeedUrl) -> None:
        assert _extract_comments_reference("/comments", feed_url) == Reference(
            kind=ReferenceKind.comments,
            url=_absolute_url("https://example.com/comments"),
            title="Comments",
        )


class TestExtractAuthorReference:

    def test_returns_none_when_href_is_missing(self, feed_url: FeedUrl) -> None:
        assert _extract_author_reference({"name": "Author"}, feed_url) is None

    def test_returns_author_reference(self, feed_url: FeedUrl) -> None:
        assert _extract_author_reference({"href": "/author", "name": "Author"}, feed_url) == Reference(
            kind=ReferenceKind.author,
            url=_absolute_url("https://example.com/author"),
            title="Author",
        )


class TestExtractEnclosureReference:

    def test_returns_none_when_href_is_missing(self, feed_url: FeedUrl) -> None:
        assert _extract_enclosure_reference({}, feed_url) is None

    def test_returns_reference(self, feed_url: FeedUrl) -> None:
        assert _extract_enclosure_reference(
            {"href": "/file.pdf", "type": "application/pdf", "title": "File", "length": "42"},
            feed_url,
        ) == Reference(
            kind=ReferenceKind.document,
            url=_absolute_url("https://example.com/file.pdf"),
            title="File",
            mime_type="application/pdf",
            size=42,
        )


class TestMergeReferencesList:

    def test_merges_duplicates(self) -> None:
        references = [
            Reference(kind=ReferenceKind.page, url=_absolute_url("https://example.com/b"), title="page"),
            Reference(
                kind=ReferenceKind.comments,
                url=_absolute_url("https://example.com/b"),
                title="comments",
            ),
        ]

        assert len(_merge_references_list(references)) == 1

    def test_returns_references_sorted_by_url(self) -> None:
        references = [
            Reference(kind=ReferenceKind.page, url=_absolute_url("https://example.com/b")),
            Reference(kind=ReferenceKind.page, url=_absolute_url("https://example.com/a")),
        ]

        assert _merge_references_list(references) == [
            Reference(kind=ReferenceKind.page, url=_absolute_url("https://example.com/a")),
            Reference(kind=ReferenceKind.page, url=_absolute_url("https://example.com/b")),
        ]


class TestExtractReferencesRaw:

    def test_collects_references_and_filters_primary_url(self, feed_url: FeedUrl) -> None:
        primary_url = _absolute_url("https://example.com/news")
        references = _extract_references_raw(
            {
                "links": [
                    {"href": "https://example.com/news", "rel": "alternate", "type": "text/html"},
                    {"href": "/page", "rel": "alternate", "type": "text/html"},
                ],
                "enclosures": [{"href": "/file.pdf", "type": "application/pdf"}],
                "media_content": [{"url": "/video", "type": "video/mp4"}],
                "media_thumbnail": [{"url": "/image"}],
                "comments": "/comments",
                "author_detail": {"href": "/author", "name": "Author"},
                "contributors": [{"href": "/contributor", "name": "Contributor"}],
            },
            feed_url,
            primary_url,
        )

        assert references == [
            Reference(kind=ReferenceKind.page, url=_absolute_url("https://example.com/page"), mime_type="text/html"),
            Reference(
                kind=ReferenceKind.document,
                url=_absolute_url("https://example.com/file.pdf"),
                mime_type="application/pdf",
            ),
            Reference(
                kind=ReferenceKind.video,
                url=_absolute_url("https://example.com/video"),
                mime_type="video/mp4",
            ),
            Reference(kind=ReferenceKind.image, url=_absolute_url("https://example.com/image")),
            Reference(
                kind=ReferenceKind.comments,
                url=_absolute_url("https://example.com/comments"),
                title="Comments",
            ),
            Reference(
                kind=ReferenceKind.author,
                url=_absolute_url("https://example.com/author"),
                title="Author",
            ),
            Reference(
                kind=ReferenceKind.author,
                url=_absolute_url("https://example.com/contributor"),
                title="Contributor",
            ),
        ]


class TestExtractReferences:

    def test_merges_duplicates_and_sorts(self, feed_url: FeedUrl) -> None:
        references = _extract_references(
            {
                "links": [{"href": "/b", "rel": "alternate", "type": "text/html"}],
                "comments": "/b",
                "media_thumbnail": [{"url": "/a"}],
            },
            feed_url,
            _absolute_url("https://example.com/news"),
        )

        assert references == [
            Reference(kind=ReferenceKind.image, url=_absolute_url("https://example.com/a")),
            Reference(
                kind=ReferenceKind.comments,
                url=_absolute_url("https://example.com/b"),
                title="Comments",
                mime_type="text/html",
            ),
        ]


class TestParseStream:

    def test_delegates_to_feedparser(self, mocker: MockerFixture) -> None:
        input_stream = io.BytesIO(b"feed")
        expected = object()
        parse = mocker.patch("feedparser.parse", return_value=expected)

        assert _parse_stream(input_stream) is expected
        parse.assert_called_once_with(input_stream)


class TestParseIntoFeedparser:

    def test_returns_channel(self, mocker: MockerFixture) -> None:
        channel = object()
        mocker.patch("ffun.parsers.feed._parse_stream", return_value=channel)

        assert parse_into_feedparser("<rss />") is channel

    def test_returns_none_and_logs_on_error(self, mocker: MockerFixture) -> None:
        mocker.patch("ffun.parsers.feed._parse_stream", side_effect=ValueError("boom"))

        with capture_logs() as logs:
            result = parse_into_feedparser("<rss />")

        assert result is None
        assert_logs(logs, error_while_parsing_feed=1)
