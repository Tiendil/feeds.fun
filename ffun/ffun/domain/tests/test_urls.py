import pytest
from furl import furl

from ffun.domain import errors, urls
from ffun.domain.entities import AbsoluteUrl, FeedUrl, SourceUid, UnknownUrl, UrlUid


class TestAdjustClassicUrl:
    @pytest.mark.parametrize(
        "original_url, raw_url, adjusted_url",
        [
            ("https://example.com/feed/", "https://example.com", "https://example.com"),
            ("https://example.com/feed/", "https://example.com/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            (
                "https://example.com/feed/",
                "http://another.domain.com:666/path/a/b?c=d",
                "http://another.domain.com:666/path/a/b?c=d",
            ),
            (
                "https://example.com/feed/",
                "another.domain.com:666/path/a/b?c=d",
                "https://another.domain.com:666/path/a/b?c=d",
            ),
            (
                "https://example.com/feed/",
                "another.domain.com/path/a/b?c=d",
                "https://another.domain.com/path/a/b?c=d",
            ),
            ("https://example.com/feed/", "/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("https://example.com/feed/", "path/a/b?c=d", "https://example.com/feed/path/a/b?c=d"),
            ("https://example.com/feed/", "path", "https://example.com/feed/path"),
            ("https://example.com/feed/", "?c=d", "https://example.com/feed/?c=d"),
            ("https://example.com/feed/", "another.domain.com", "https://another.domain.com"),
            ("https://example.com", "another.domain.com/path/a/b?c=d", "https://another.domain.com/path/a/b?c=d"),
            ("https://example.com", "/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("https://example.com", "path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("https://example.com", "path", "https://example.com/path"),
            ("https://example.com", "?c=d", "https://example.com?c=d"),
            ("https://example.com", "another.domain.com", "https://another.domain.com"),
            ("//example.com/feed/", "https://example.com", "https://example.com"),
            ("//example.com/feed/", "example.com/path/a/b?c=d", "//example.com/path/a/b?c=d"),
            (
                "//example.com/feed/",
                "http://another.domain.com:666/path/a/b?c=d",
                "http://another.domain.com:666/path/a/b?c=d",
            ),
            ("//example.com/feed/", "another.domain.com:666/path/a/b?c=d", "//another.domain.com:666/path/a/b?c=d"),
            ("//example.com/feed/", "another.domain.com/path/a/b?c=d", "//another.domain.com/path/a/b?c=d"),
            ("//example.com/feed/", "/path/a/b?c=d", "//example.com/path/a/b?c=d"),
            ("//example.com/feed/", "path/a/b?c=d", "//example.com/feed/path/a/b?c=d"),
            ("//example.com/feed/", "path", "//example.com/feed/path"),
            ("//example.com/feed/", "?c=d", "//example.com/feed/?c=d"),
            ("//example.com/feed/", "another.domain.com", "//another.domain.com"),
            # test keeping fragment
            (
                "https://example.com/feed/",
                "https://example.com/path/a/b?c=d#fragment",
                "https://example.com/path/a/b?c=d#fragment",
            ),
            ("//example.com/feed/", "/path/a/b?c=d#z=q", "//example.com/path/a/b?c=d#z=q"),
        ],
    )
    def test_base_transformations(
        self, original_url: AbsoluteUrl, raw_url: UnknownUrl, adjusted_url: AbsoluteUrl
    ) -> None:
        assert urls.is_absolute_url(original_url)
        assert urls.is_absolute_url(adjusted_url)

        assert urls.adjust_classic_url(raw_url, original_url) == adjusted_url


class TestIsMagneticUrl:
    @pytest.mark.parametrize(
        "url, is_magnetic",
        [
            (
                "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80",  # noqa
                True,
            ),
            ("https://example.com/path/a/b?c=d", False),
            ("http://another.domain.com:666/path/a/b?c=d", False),
        ],
    )
    def test(self, url: UnknownUrl, is_magnetic: bool) -> None:
        assert urls.is_magnetic_url(url) == is_magnetic


class TestAdjustMagneticUrl:
    def test(self) -> None:
        url = "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80"  # noqa
        assert urls.adjust_magnetic_url(UnknownUrl(url)) == url


class TestAdjustExternalUrl:
    @pytest.mark.parametrize(
        "url, adjusted_url",
        [
            ("https://example.com/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            ("http://another.domain.com:666/path/a/b?c=d", "http://another.domain.com:666/path/a/b?c=d"),
            ("/path/a/b?c=d", "https://example.com/path/a/b?c=d"),
            (
                "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80",  # noqa
                "magnet:?xt=urn:btih:123456789abcdef0123456789abcdef0123456789&dn=Example+File.mp4&tr=udp%3A%2F%2Ftracker.example.com%3A80",  # noqa
            ),
            ("http://www.usinenouvelle.comhttps://www.usine-digitale.fr/article/christophe", None),
            ("x" * 100, "https://example.com/" + "x" * 100),  # noqa
            ("x-x" * 100, "https://example.com/" + "x-x" * 100),  # noqa
            ("xxx.com", "https://xxx.com"),  # noqa
            ("x" * 100 + ".html", "https://example.com/" + "x" * 100 + ".html"),  # noqa
            ("x.html", "https://example.com/x.html"),  # noqa
            # TODO: what if ip addreses?
        ],
    )
    def test(self, url: UnknownUrl, adjusted_url: AbsoluteUrl) -> None:
        assert (
            adjusted_url is None or urls.is_absolute_url(adjusted_url) or urls.is_magnetic_url(url)
        ), "Wrong test parameters"

        original_url = urls.normalize_classic_unknown_url(UnknownUrl("https://example.com"))

        assert original_url is not None

        assert urls.adjust_external_url(url, original_url=original_url) == adjusted_url


class TestUrlToUid:
    # This parameters are a bit excessive
    # Current implementation of url_to_uid expects already normalized AbsoluteUrl
    @pytest.mark.parametrize(
        "url, uid",
        [  # strip spaces
            ("   //example.com", "example.com"),
            ("//example.com   ", "example.com"),
            # trailing slash
            ("//example.com/", "example.com"),
            ("//example.com//", "example.com"),
            ("//example.com/path/", "example.com/path"),
            # uppercase
            ("//EXAMPLE.COM", "example.com"),
            ("//exaMple.com/somE/pAth", "example.com/some/path"),
            # pluses
            ("//example.com/with+plus", "example.com/with+plus"),
            ("//example.com/with%20space", "example.com/with+space"),
            ("//example.com/with plus", "example.com/with+plus"),
            # quotes
            ("//example.com/with%22quote", 'example.com/with"quote'),
            ("//example.com/with%27quote", "example.com/with'quote"),
            # query
            ("//example.com/?a=b&c=d", "example.com?a=b&c=d"),
            ("//example.com/?c=d&a=b", "example.com?a=b&c=d"),
            # query with quotes
            ("//example.com/?a=%22b%22", 'example.com?a="b"'),
            ("//example.com/?a=%27b%27", "example.com?a='b'"),
            # complext query with duplicates and sorting
            ("//example.com/?c=d&a=g&e=f&a=b", "example.com?a=b&a=g&c=d&e=f"),
            # duble slashes
            ("//example.com//path//to//resource", "example.com/path/to/resource"),
            # unicode normalization
            ("//example.com/%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82", "example.com/привет"),
            # unicode complex symbols
            ("//example.com/%E2%98%83", "example.com/☃"),
            # unicode NFD to NFC
            ("//example.com/й", "example.com/й"),
            # remove schema
            ("http://example.com", "example.com"),
            ("https://example.com", "example.com"),
            ("ftp://example.com", "example.com"),
            ("//example.com", "example.com"),
            # remove ports
            ("//example.com:666", "example.com"),
            ("//example.com:666/path", "example.com/path"),
            ("//example.com:80", "example.com"),
            ("//example.com:443/path", "example.com/path"),
            # remove fragment
            ("//example.com#fragment", "example.com"),
            ("//example.com/path#fragment", "example.com/path"),
            ("//example.com/path#fragment?query", "example.com/path"),
            ("//example.com/path?query#", "example.com/path?query"),
        ],
    )
    def test(self, url: AbsoluteUrl, uid: UrlUid) -> None:
        assert urls.url_to_uid(url) == uid


class TestUrlToSourceUid:

    # This parameters are a bit excessive
    # Current implementation of url_to_uid expects already normalized AbsoluteUrl
    @pytest.mark.parametrize(
        "url, source_uid",
        [
            ("   //example.com   ", "example.com"),
            ("//example.com/path/a/b?x=y", "example.com"),
            ("//ExamPle.com", "example.com"),
            ("//www.example.com", "example.com"),
            ("//subdomain.example.com", "subdomain.example.com"),
            ("//old.reddit.com", "reddit.com"),
            ("//api.reddit.com", "reddit.com"),
            ("http://api.reddit.com", "reddit.com"),
            ("https://api.reddit.com", "reddit.com"),
            ("ftp://api.reddit.com", "reddit.com"),
            ("//programming.reddit.com", "reddit.com"),
            ("//anotherreddit.com", "anotherreddit.com"),
            ("//xxx.anotherreddit.com", "xxx.anotherreddit.com"),
            # unicode normalization
            ("//фвыа.com", "фвыа.com"),
        ],
    )
    def test(self, url: AbsoluteUrl, source_uid: SourceUid) -> None:
        assert urls.url_to_source_uid(url) == source_uid


class TestCheckFurlError:

    def test_invalid_port(self) -> None:
        with pytest.raises(errors.ExpectedFUrlError):
            with urls.check_furl_error():
                furl("https://example.com:666666")

    def test_another_error(self) -> None:
        with pytest.raises(ZeroDivisionError):
            with urls.check_furl_error():
                1 / 0


class TestFixClassicUrlToAbsolute:

    def test_no_dot_in_domain(self) -> None:
        assert urls._fix_classic_url_to_absolute("localhost") is None
        assert urls._fix_classic_url_to_absolute("examplecom") is None

    def test_no_public_suffix(self) -> None:
        assert urls._fix_classic_url_to_absolute("example") is None
        assert urls._fix_classic_url_to_absolute("example.myprivatezone") is None

    def test_can_not_construct_furl(self) -> None:
        assert urls._fix_classic_url_to_absolute("example.com:666666") is None

    def test_ok(self) -> None:
        assert urls._fix_classic_url_to_absolute("example.com") == "//example.com"
        assert urls._fix_classic_url_to_absolute("example.com/path") == "//example.com/path"
        assert urls._fix_classic_url_to_absolute("example.com/path?x=y") == "//example.com/path?x=y"
        assert urls._fix_classic_url_to_absolute("example.com/path?x=y#fragment") == "//example.com/path?x=y#fragment"


class TestNormalizeClassicUnknownUrl:

    def test_general_sceme(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("//example.com?")) == "//example.com"

    def test_relative_same_level(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("./a/b?x=y")) is None

    def test_relative_upper_level(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("../a/b?x=y")) is None
        assert urls.normalize_classic_unknown_url(UnknownUrl("../../a/b?x=y")) is None

    def test_furl_error(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("//example.com:9999999?")) is None

    def test_has_scheme(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("http://example.com?")) == "http://example.com"
        assert urls.normalize_classic_unknown_url(UnknownUrl("https://example.com?")) == "https://example.com"

    def test_no_domain(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("a/b?x=y")) is None
        assert urls.normalize_classic_unknown_url(UnknownUrl("localhost/x/y?a=b")) is None

    def test_ok(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com/a/b/c?x=y")) == "//example.com/a/b/c?x=y"

    def test_keepsegment(self) -> None:
        # short logic path
        assert (
            urls.normalize_classic_unknown_url(UnknownUrl("//example.com/a/b/c?x=y#z")) == "//example.com/a/b/c?x=y#z"
        )

        # longest logic path
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com/a/b/c?x=y#z")) == "//example.com/a/b/c?x=y#z"

    def remove_trailing_root_slash(self) -> None:
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com")) == "//example.com"
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com/")) == "//example.com"
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com//")) == "//example.com"
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com///")) == "//example.com"
        assert urls.normalize_classic_unknown_url(UnknownUrl("example.com////")) == "//example.com"


class TestIsFullUrl:

    def test(self) -> None:
        assert urls.is_full_url(UnknownUrl("http://example.com"))
        assert not urls.is_full_url(UnknownUrl("abc"))


class TestStrToAbsoluteUrl:

    def test_ok(self) -> None:
        assert urls.str_to_absolute_url("http://example.com?") == "http://example.com"

    def test_not_ok(self) -> None:
        with pytest.raises(errors.UrlIsNotAbsolute):
            assert urls.str_to_absolute_url("example_com")


class TestStrToFeedUrl:

    def test_ok(self) -> None:
        assert urls.str_to_feed_url("http://example.com?") == "http://example.com"

    def test_not_ok(self) -> None:
        with pytest.raises(errors.UrlIsNotAbsolute):
            assert urls.str_to_feed_url("example_com")


class TestIsAbsoluteUrl:

    def test_ok(self) -> None:
        assert urls.is_absolute_url("http://example.com")

    def test_not_ok(self) -> None:
        assert not urls.is_absolute_url("http://example.com?")


class TestAdjustClassicFullUrl:

    def test_no_schema(self) -> None:
        assert (
            urls.adjust_classic_full_url(UnknownUrl("example.com"), urls.str_to_absolute_url("https://example.com"))
            == "https://example.com"
        )
        assert (
            urls.adjust_classic_full_url(UnknownUrl("example.com"), urls.str_to_absolute_url("http://example.com"))
            == "http://example.com"
        )

        assert (
            urls.adjust_classic_full_url(UnknownUrl("abc.com"), urls.str_to_absolute_url("http://example.com"))
            == "http://abc.com"
        )
        assert (
            urls.adjust_classic_full_url(UnknownUrl("abc.com"), urls.str_to_absolute_url("https://example.com"))
            == "https://abc.com"
        )

    def test_has_schema(self) -> None:
        assert (
            urls.adjust_classic_full_url(
                UnknownUrl("https://example.com"), urls.str_to_absolute_url("https://example.com")
            )
            == "https://example.com"
        )
        assert (
            urls.adjust_classic_full_url(
                UnknownUrl("https://example.com"), urls.str_to_absolute_url("http://example.com")
            )
            == "https://example.com"
        )

        assert (
            urls.adjust_classic_full_url(UnknownUrl("http://abc.com"), urls.str_to_absolute_url("http://example.com"))
            == "http://abc.com"
        )
        assert (
            urls.adjust_classic_full_url(UnknownUrl("http://abc.com"), urls.str_to_absolute_url("https://example.com"))
            == "http://abc.com"
        )


class TestAdjustClassicRelativeUrl:

    def test_cleanup_original(self) -> None:
        assert (
            urls.adjust_classic_relative_url(UnknownUrl("a/b"), urls.str_to_absolute_url("https://example.com?x=y#z"))
            == "https://example.com/a/b"
        )

    def test_same_level(self) -> None:
        assert (
            urls.adjust_classic_relative_url(
                UnknownUrl("./a/b"), urls.str_to_absolute_url("https://example.com/feed/part?x=y#z")
            )
            == "https://example.com/feed/a/b"
        )

    def test_upper_level(self) -> None:
        assert (
            urls.adjust_classic_relative_url(
                UnknownUrl("../a/b"), urls.str_to_absolute_url("https://example.com/feed/part?x=y#z")
            )
            == "https://example.com/a/b"
        )


class TestUrlHasExtension:

    def test_no_path(self) -> None:
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com/"), [".xml"])
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com"), [".xml"])
        assert urls.url_has_extension(urls.str_to_absolute_url("https://example.com/"), [""])
        assert urls.url_has_extension(urls.str_to_absolute_url("https://example.com"), [""])
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com/"), [])
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com"), [])

    def test_has(self) -> None:
        assert urls.url_has_extension(urls.str_to_absolute_url("https://example.com/feed.xml"), [".xml"])
        assert urls.url_has_extension(urls.str_to_absolute_url("https://example.com/feed.second..xml"), [".xml"])
        assert urls.url_has_extension(
            urls.str_to_absolute_url("https://example.com/feed.second.xml"), [".rss", ".xml", ".html"]
        )
        assert urls.url_has_extension(urls.str_to_absolute_url("https://example.com/feed/second"), [""])

    def test_has_no(self) -> None:
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com/feed.xml"), [])
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com/feed.second..xml"), [])
        assert not urls.url_has_extension(
            urls.str_to_absolute_url("https://example.com/feed.second.xml"), [".rss", ".html"]
        )
        assert not urls.url_has_extension(urls.str_to_absolute_url("https://example.com/feed/second"), [])


class TestFilterOutDuplicatedUrls:

    def test_no_urls(self) -> None:
        assert urls.filter_out_duplicated_urls([]) == []

    def test_no_duplicates(self) -> None:
        assert urls.filter_out_duplicated_urls(
            [
                urls.str_to_absolute_url("https://example.com/feed1"),
                urls.str_to_absolute_url("https://example.com/feed2"),
            ]
        ) == [
            "https://example.com/feed1",
            "https://example.com/feed2",
        ]

    def test_duplicates(self) -> None:
        assert urls.filter_out_duplicated_urls(
            [
                urls.str_to_absolute_url("https://example.com/feed1?a=b&c=d"),
                urls.str_to_absolute_url("https://example.com/feed2"),
                urls.str_to_absolute_url("https://example.com/feed1?c=d&a=b"),
            ]
        ) == ["https://example.com/feed1?a=b&c=d", "https://example.com/feed2"]


class TestGetParentUrl:

    def test_no_parent(self) -> None:
        assert urls.get_parent_url(urls.str_to_absolute_url("https://example.com")) is None
        assert urls.get_parent_url(urls.str_to_absolute_url("https://example.com/")) is None
        assert urls.get_parent_url(urls.str_to_absolute_url("https://subdomain.example.com")) is None

    def test_has_parent(self) -> None:
        assert urls.get_parent_url(urls.str_to_absolute_url("https://example.com/feed")) == "https://example.com"
        assert urls.get_parent_url(urls.str_to_absolute_url("https://example.com/feed/")) == "https://example.com/feed"
        assert (
            urls.get_parent_url(urls.str_to_absolute_url("https://example.com/feed/part"))
            == "https://example.com/feed/"
        )
        assert urls.get_parent_url(urls.str_to_absolute_url("https://example.com/feed/")) == "https://example.com/feed"
        assert (
            urls.get_parent_url(urls.str_to_absolute_url("https://subdomain.example.com/feed/part"))
            == "https://subdomain.example.com/feed/"
        )
        assert (
            urls.get_parent_url(urls.str_to_absolute_url("https://example.com/feed/part/second"))
            == "https://example.com/feed/part/"
        )


class TestToFeedUrl:

    @pytest.mark.parametrize(
        "url, feed_url",
        [
            ("https://example.com/feed", "https://example.com/feed"),
            ("https://example.com/feed/", "https://example.com/feed/"),
            ("https://example.com/feed#fragment", "https://example.com/feed"),
        ],
    )
    def test(self, url: AbsoluteUrl, feed_url: FeedUrl) -> None:
        assert urls.to_feed_url(url) == feed_url
