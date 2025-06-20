import datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

from ffun.core import json, utils
from ffun.core.tests.helpers import assert_logs, capture_logs
from ffun.domain.entities import FeedUrl, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url
from ffun.parsers.entities import EntryInfo, FeedInfo
from ffun.parsers.feed import _extract_published_at, parse_entry, parse_feed
from ffun.parsers.tests.helpers import feeds_fixtures_directory, feeds_fixtures_names


class TestParseEntry:

    def test_parse(self) -> None:
        raw_entry = {
            "title": "Entry title 1",
            "link": "/2023/07/25/news-1.html",
            "published_parsed": (2023, 7, 25, 17, 15, 0, 0, 0, -1),
            "description": "Body 1",
            "tags": [
                {"term": "tag1"},
                {"term": "tag2"},
                {"label": "tag3"},
            ],
        }

        original_url = normalize_classic_unknown_url(UnknownUrl("https://example.com/feed/"))

        assert original_url is not None

        parsed_entry = parse_entry(raw_entry, to_feed_url(original_url))

        expected_entry = EntryInfo(
            title="Entry title 1",
            body="Body 1",
            external_id="/2023/07/25/news-1.html",
            external_url=normalize_classic_unknown_url(UnknownUrl("https://example.com/2023/07/25/news-1.html")),
            published_at=datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc),
            external_tags={"tag1", "tag2", "tag3"},
        )

        assert parsed_entry == expected_entry


class TestParseFeed:

    def test_error_in_feedparser(self, mocker: MockerFixture) -> None:
        url = normalize_classic_unknown_url(UnknownUrl("https://example.com/feed/"))

        assert url is not None

        mocker.patch("feedparser.parse", side_effect=ValueError("Test error in feedparser"))

        with capture_logs() as logs:
            feed_info = parse_feed("", to_feed_url(url))

        assert feed_info is None
        assert_logs(logs, error_while_parsing_feed=1)

    @pytest.mark.parametrize("raw_fixture_name", feeds_fixtures_names())
    def test_on_row_fixtures(self, raw_fixture_name: str) -> None:
        raw_fixture_path = feeds_fixtures_directory / raw_fixture_name
        expected_fixture_path = str(raw_fixture_path) + ".expected.json"

        with open(raw_fixture_path, "r", encoding="utf-8") as raw_fixture_file:
            raw_fixture = raw_fixture_file.read()

        with open(expected_fixture_path, "r", encoding="utf-8") as expected_fixture_file:
            expected_fixture = expected_fixture_file.read()

        url = normalize_classic_unknown_url(UnknownUrl("https://example.com/feed/"))

        assert url is not None

        feed_info = parse_feed(raw_fixture, to_feed_url(url))

        assert feed_info == FeedInfo.model_validate_json(expected_fixture)

    @pytest.mark.parametrize("raw_fixture_name", feeds_fixtures_names())
    def test_skip_entry_on_error(self, raw_fixture_name: str, mocker: MockerFixture) -> None:
        raw_fixture_path = feeds_fixtures_directory / raw_fixture_name
        expected_fixture_path = str(raw_fixture_path) + ".expected.json"

        with open(raw_fixture_path, "r", encoding="utf-8") as raw_fixture_file:
            raw_fixture = raw_fixture_file.read()

        with open(expected_fixture_path, "r", encoding="utf-8") as expected_fixture_file:
            expected_fixture = expected_fixture_file.read()

        url = normalize_classic_unknown_url(UnknownUrl("https://example.com/feed/"))

        assert url is not None

        call_number = {"calls": 0}

        def mocked_parse_entry(raw_entry: Any, original_url: FeedUrl) -> EntryInfo:
            call_number["calls"] += 1

            if call_number["calls"] == 1:
                raise ValueError("Test error on entry parsing")

            return parse_entry(raw_entry, original_url)

        mocker.patch("ffun.parsers.feed.parse_entry", side_effect=mocked_parse_entry)

        with capture_logs() as logs:
            feed_info = parse_feed(raw_fixture, to_feed_url(url))

        assert_logs(logs, error_while_parsing_feed_entry=1)

        # the first entry will be skipped due to the error in parsing
        parsed_expected_fixture = json.parse(expected_fixture)
        parsed_expected_fixture["entries"] = parsed_expected_fixture["entries"][1:]

        assert feed_info == FeedInfo.model_validate(parsed_expected_fixture)


class TestExtractPublishedAt:

    def test_ok(self) -> None:
        published_parsed = (2023, 7, 25, 17, 15, 0, 0, 0, -1)
        expected_published_at = datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc)
        assert _extract_published_at({"published_parsed": published_parsed}) == expected_published_at

    def test_value_error(self) -> None:
        published_parsed = (1, 1, 1, 0, 0, 0, 0, 1, 0)
        assert (utils.now() - _extract_published_at({"published_parsed": published_parsed})).total_seconds() < 1
