import os

import pytest

from ffun.parsers.entities import FeedInfo
from ffun.parsers.feed import _normalize_external_url, parse_feed

feeds_fixtures_directory = os.path.join(os.path.dirname(__file__), 'feeds_fixtures')


_excluded_suffixes = ['.expected.json', '~', '#']


def _feeds_fixtures_names() -> list[str]:
    files = os.listdir(feeds_fixtures_directory)

    return [filename
            for filename in files
            if not any(filename.endswith(suffix) for suffix in _excluded_suffixes)]


class TestParseFeed:

    @pytest.mark.parametrize('raw_fixture_name', _feeds_fixtures_names())
    def test_on_row_fixtures(self, raw_fixture_name: str) -> None:
        raw_fixture_path = os.path.join(feeds_fixtures_directory, raw_fixture_name)
        expected_fixture_path = raw_fixture_path + '.expected.json'

        with open(raw_fixture_path, 'r', encoding='utf-8') as raw_fixture_file:
            raw_fixture = raw_fixture_file.read()

        with open(expected_fixture_path, 'r', encoding='utf-8') as expected_fixture_file:
            expected_fixture = expected_fixture_file.read()

        feed_info = parse_feed(raw_fixture, 'https://example.com/feed/')

        assert feed_info == FeedInfo.model_validate_json(expected_fixture)


class TestExternalUrlNormalization:

    @pytest.mark.parametrize('original_url, raw_url, normalized_url', [
        ('https://example.com/feed/', 'https://example.com', 'https://example.com'),
        ('https://example.com/feed/', 'https://example.com/path/a/b?c=d', 'https://example.com/path/a/b?c=d'),
        ('https://example.com/feed/', 'http://another.domain:666/path/a/b?c=d', 'http://another.domain:666/path/a/b?c=d'),
        ('https://example.com/feed/', 'another.domain:666/path/a/b?c=d', 'https://another.domain:666/path/a/b?c=d'),
        ('https://example.com/feed/', 'another.domain/path/a/b?c=d', 'https://another.domain/path/a/b?c=d'),
        ('https://example.com/feed/', '/path/a/b?c=d', 'https://example.com/path/a/b?c=d'),
        ('https://example.com/feed/', 'path/a/b?c=d', 'https://example.com/path/a/b?c=d'),
        ('https://example.com/feed/', 'path', 'https://example.com/path'),
        ('https://example.com/feed/', '?c=d', 'https://example.com?c=d'),
        ('https://example.com/feed/', 'another.domain', 'https://another.domain'),

        ('example.com/feed/', 'https://example.com', 'https://example.com'),
        ('example.com/feed/', 'example.com/path/a/b?c=d', 'example.com/path/a/b?c=d'),
        ('example.com/feed/', 'http://another.domain:666/path/a/b?c=d', 'http://another.domain:666/path/a/b?c=d'),
        ('example.com/feed/', 'another.domain:666/path/a/b?c=d', 'another.domain:666/path/a/b?c=d'),
        ('example.com/feed/', 'another.domain/path/a/b?c=d', 'another.domain/path/a/b?c=d'),
        ('example.com/feed/', '/path/a/b?c=d', 'example.com/path/a/b?c=d'),
        ('example.com/feed/', 'path/a/b?c=d', 'example.com/path/a/b?c=d'),
        ('example.com/feed/', 'path', 'example.com/path'),
        ('example.com/feed/', '?c=d', 'example.com?c=d'),
        ('example.com/feed/', 'another.domain', 'another.domain'),
    ])
    def test_base_transformations(self, original_url: str, raw_url: str, normalized_url: str) -> None:
        assert _normalize_external_url(raw_url, original_url) == normalized_url
