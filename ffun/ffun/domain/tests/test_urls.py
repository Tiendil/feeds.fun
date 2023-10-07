import pytest

from ffun.domain.urls import normalize_external_url


class TestExternalUrlNormalization:
    @pytest.mark.parametrize(
        "original_url, raw_url, normalized_url",
        [
            ("https://example.com/feed/", "https://example.com", "https://example.com"),
            ("https://example.com/feed/", "https://example.com/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            (
                "https://example.com/feed/",
                "http://another.domain:666/path/a/b?c=d",
                "http://another.domain:666/path/a/b?c=d",
            ),
            (
                "https://example.com/feed/",
                "another.domain:666/path/a/b?c=d",
                "https://another.domain:666/path/a/b?c=d",
            ),
            ("https://example.com/feed/", "another.domain/path/a/b?c=d", "https://another.domain/path/a/b?c=d"),
            ("https://example.com/feed/", "/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("https://example.com/feed/", "path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("https://example.com/feed/", "path", "https://example.com/path"),
            ("https://example.com/feed/", "?c=d", "https://example.com?c=d"),
            ("https://example.com/feed/", "another.domain", "https://another.domain"),
            ("example.com/feed/", "https://example.com", "https://example.com"),
            ("example.com/feed/", "example.com/path/a/b?c=d", "example.com/path/a/b?c=d"),
            ("example.com/feed/", "http://another.domain:666/path/a/b?c=d", "http://another.domain:666/path/a/b?c=d"),
            ("example.com/feed/", "another.domain:666/path/a/b?c=d", "another.domain:666/path/a/b?c=d"),
            ("example.com/feed/", "another.domain/path/a/b?c=d", "another.domain/path/a/b?c=d"),
            ("example.com/feed/", "/path/a/b?c=d", "example.com/path/a/b?c=d"),
            ("example.com/feed/", "path/a/b?c=d", "example.com/path/a/b?c=d"),
            ("example.com/feed/", "path", "example.com/path"),
            ("example.com/feed/", "?c=d", "example.com?c=d"),
            ("example.com/feed/", "another.domain", "another.domain"),
        ],
    )
    def test_base_transformations(self, original_url: str, raw_url: str, normalized_url: str) -> None:
        assert normalize_external_url(raw_url, original_url) == normalized_url
