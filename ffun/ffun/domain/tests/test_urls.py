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


class TestUrlToUid:
    @pytest.mark.parametrize(
        "url, uid",
        [  # strip spaces
            ("   example.com", "example.com"),
            ("example.com   ", "example.com"),
            # trailing slash
            ("example.com/", "example.com"),
            ("example.com//", "example.com"),
            ("example.com/path/", "example.com/path"),
            # uppercase
            ("EXAMPLE.COM", "example.com"),
            ("exaMple.com/somE/pAth", "example.com/some/path"),
            # pluses
            ("example.com/with+plus", "example.com/with+plus"),
            ("example.com/with%20space", "example.com/with+space"),
            ("example.com/with plus", "example.com/with+plus"),
            # quotes
            ("example.com/with%22quote", 'example.com/with"quote'),
            ("example.com/with%27quote", "example.com/with'quote"),
            # query
            ("example.com/?a=b&c=d", "example.com?a=b&c=d"),
            ("example.com/?c=d&a=b", "example.com?a=b&c=d"),
            # query with quotes
            ("example.com/?a=%22b%22", 'example.com?a="b"'),
            ("example.com/?a=%27b%27", "example.com?a='b'"),
            # complext query with duplicates and sorting
            ("example.com/?c=d&a=g&e=f&a=b", "example.com?a=b&a=g&c=d&e=f"),
            # duble slashes
            ("example.com//path//to//resource", "example.com/path/to/resource"),
            # unicode normalization
            ("example.com/%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82", "example.com/привет"),
            # unicode complex symbols
            ("example.com/%E2%98%83", "example.com/☃"),
            # unicode NFD to NFC
            ("example.com/й", "example.com/й"),
            # remove schema
            ("http://example.com", "example.com"),
            ("https://example.com", "example.com"),
            ("ftp://example.com", "example.com"),
            ("//example.com", "example.com"),
            # remove ports
            ("example.com:666", "example.com"),
            ("example.com:666/path", "example.com/path"),
            ("example.com:80", "example.com"),
            ("example.com:443/path", "example.com/path"),
            # remove fragment
            ("example.com#fragment", "example.com"),
            ("example.com/path#fragment", "example.com/path"),
            ("example.com/path#fragment?query", "example.com/path"),
            ("example.com/path?query#", "example.com/path?query"),
        ],
    )
    def test(self, url: str, uid: str) -> None:
        assert urls.url_to_uid(url) == uid
