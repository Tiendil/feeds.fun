import pytest

from ffun.domain.entities import UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url
from ffun.parsers.entities import FeedInfo
from ffun.parsers.feed import parse_feed
from ffun.parsers.tests.helpers import feeds_fixtures_directory, feeds_fixtures_names


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
