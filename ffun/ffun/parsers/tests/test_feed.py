import os

import pytest

from ffun.parsers.entities import FeedInfo
from ffun.parsers.feed import parse_feed

feeds_fixtures_directory = os.path.join(os.path.dirname(__file__), "feeds_fixtures")


_excluded_suffixes = [".expected.json", "~", "#"]


def _feeds_fixtures_names() -> list[str]:
    files = os.listdir(feeds_fixtures_directory)

    return [filename for filename in files if not any(filename.endswith(suffix) for suffix in _excluded_suffixes)]


class TestParseFeed:
    @pytest.mark.parametrize("raw_fixture_name", _feeds_fixtures_names())
    def test_on_row_fixtures(self, raw_fixture_name: str) -> None:
        raw_fixture_path = os.path.join(feeds_fixtures_directory, raw_fixture_name)
        expected_fixture_path = raw_fixture_path + ".expected.json"

        with open(raw_fixture_path, "r", encoding="utf-8") as raw_fixture_file:
            raw_fixture = raw_fixture_file.read()

        with open(expected_fixture_path, "r", encoding="utf-8") as expected_fixture_file:
            expected_fixture = expected_fixture_file.read()

        feed_info = parse_feed(raw_fixture, "https://example.com/feed/")

        assert feed_info == FeedInfo.model_validate_json(expected_fixture)
