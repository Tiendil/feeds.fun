import pytest

from ffun.domain import urls


class TestNormalizeClassicUrl:
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
        assert urls.normalize_classic_url(raw_url, original_url) == normalized_url


class TestIsMagneticUrl:
    @pytest.mark.parametrize(
        "url, is_magnetic",
        [
            (
                "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80",  # noqa
                True,
            ),
            ("https://example.com/path/a/b?c=d", False),
            ("http://another.domain:666/path/a/b?c=d", False),
        ],
    )
    def test(self, url: str, is_magnetic: bool) -> None:
        assert urls.is_magnetic_url(url) == is_magnetic


class TestNormalizeMagneticUrl:
    def test(self) -> None:
        url = "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80"  # noqa
        assert urls.normalize_magnetic_url(url) == url


class TestNormalizeExternalUrl:
    @pytest.mark.parametrize(
        "url, normalized_url",
        [
            ("https://example.com/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("http://another.domain:666/path/a/b?c=d", "http://another.domain:666/path/a/b?c=d"),
            ("/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            (
                "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80",  # noqa
                "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80",  # noqa
            ),
        ],
    )
    def test(self, url: str, normalized_url: str) -> None:
        assert urls.normalize_external_url(url, original_url="https://example.com") == normalized_url
