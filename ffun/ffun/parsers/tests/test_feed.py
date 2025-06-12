import datetime
import pytest

from ffun.core import utils
from ffun.domain.entities import UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url
from ffun.parsers.entities import FeedInfo, EntryInfo
from ffun.parsers.feed import parse_feed, parse_entry
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

        original_url = to_feed_url(UnknownUrl("https://example.com/feed/"))

        parsed_entry = parse_entry(raw_entry, original_url)

        expected_entry = EntryInfo(
                title="Entry title 1",
                body="Body 1",
                external_id="/2023/07/25/news-1.html",
                external_url="https://example.com/2023/07/25/news-1.html",
                published_at=datetime.datetime(2023, 7, 25, 17, 15, 0, tzinfo=datetime.timezone.utc),
                external_tags={"tag1", "tag2", "tag3"},
                )

        assert parsed_entry == expected_entry


class TestParseFeed:
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
