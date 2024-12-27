import contextlib
import re
import unicodedata
from typing import Iterable, Iterator
from urllib.parse import quote_plus, unquote

import tldextract
from furl import furl
from orderedmultidict import omdict

from ffun.core import logging
from ffun.domain import errors
from ffun.domain.entities import AbsoluteUrl, FeedUrl, SourceUid, UnknownUrl, UrlUid

logger = logging.get_module_logger()


# ATTENTION: in case of modification, you MUST check:
#            - that the logic of dependent functions is not broken
#            - that the UIDs generation is not changed (check on backup)
#            - in case UIDs generation is changed, you MUST update all affected entities


RE_SCHEMA = re.compile(r"^(\w+):")


@contextlib.contextmanager
def check_furl_error() -> Iterator[None]:
    try:
        yield
    except ValueError as e:
        message = str(e)

        if "Invalid port" in message:
            raise errors.ExpectedFUrlError(message=message) from e

        raise


def construct_f_url(url: UnknownUrl | AbsoluteUrl | str) -> furl | None:
    try:
        with check_furl_error():
            return furl(url)
    except errors.ExpectedFUrlError:
        return None


def initialize_tld_cache() -> None:
    logger.info("initializing_tld_cache")
    tldextract.extract("example.com")
    logger.info("tld_cache_initialized")


# ATTENTION: see note at the top of the file
def _fix_classic_url_to_absolute(url: str) -> AbsoluteUrl | None:
    domain_part = url.split("/")[0]

    # simple protection from processing special domains
    if "." not in domain_part:
        return None

    # check if url has a proper domain
    if tldextract.extract(domain_part).suffix == "":
        return None

    f_url = construct_f_url(f"//{url}")

    if f_url is None:
        return None

    return normalize_classic_unknown_url(UnknownUrl(str(f_url)))


# ATTENTION: see note at the top of the file
def normalize_classic_unknown_url(url: UnknownUrl) -> AbsoluteUrl | None:
    url = UnknownUrl(url.strip())

    # check if url is parsable
    f_url = construct_f_url(url)

    if f_url is None:
        return None

    if f_url.path == "/":
        f_url.path = None

    if url.startswith("//"):
        return AbsoluteUrl(str(f_url))

    if url.startswith("./") or url.startswith("../"):
        return None

    if RE_SCHEMA.match(url):
        return AbsoluteUrl(str(f_url))

    return _fix_classic_url_to_absolute(url)


# ATTENTION: see note at the top of the file
def is_full_url(url: UnknownUrl) -> bool:
    return normalize_classic_unknown_url(url) is not None


# it is a shortcut method for tests
def str_to_absolute_url(url: str) -> AbsoluteUrl:
    """Convert or raise Exception

    It is shortcut method mostly for tests.
    Use `normalize_classic_unknown_url` in the production code.
    """
    absolute_url = normalize_classic_unknown_url(UnknownUrl(url))

    if absolute_url is None:
        raise errors.UrlIsNotAbsolute(url=url)

    return absolute_url


# it is a shortcut method for tests
def str_to_feed_url(url: str) -> FeedUrl:
    return to_feed_url(str_to_absolute_url(url))


# ATTENTION: see note at the top of the file
def is_absolute_url(url: str) -> bool:
    """Check if the URL is absolute and is normalized"""
    return normalize_classic_unknown_url(UnknownUrl(url)) == url


# ATTENTION: see note at the top of the file
def adjust_classic_full_url(url: UnknownUrl, original_url: AbsoluteUrl | FeedUrl) -> AbsoluteUrl | None:
    fixed_url = normalize_classic_unknown_url(url)
    assert fixed_url is not None

    f_original_url = furl(original_url)
    f_url = furl(fixed_url)

    # own schema has priority over origin schema
    # we expect that owner of site (who specify urls) know what they are doing
    if not f_url.scheme:
        f_url.scheme = f_original_url.scheme

    return AbsoluteUrl(str(f_url))


# ATTENTION: see note at the top of the file
def adjust_classic_relative_url(url: UnknownUrl, original_url: AbsoluteUrl | FeedUrl) -> AbsoluteUrl | None:
    f_url = construct_f_url(original_url)

    if f_url is None:
        return None

    f_url.remove(query_params=True, fragment=True)

    try:
        with check_furl_error():
            f_url.join(url)
    except errors.ExpectedFUrlError:
        return None

    return AbsoluteUrl(str(f_url))


# ATTENTION: see note at the top of the file
def adjust_classic_url(url: UnknownUrl, original_url: AbsoluteUrl | FeedUrl) -> AbsoluteUrl | None:
    if is_full_url(url):
        return adjust_classic_full_url(url, original_url)

    return adjust_classic_relative_url(url, original_url)


def is_magnetic_url(url: UnknownUrl) -> bool:
    return url.startswith("magnet:")


def adjust_magnetic_url(url: UnknownUrl) -> AbsoluteUrl:
    return AbsoluteUrl(url)


# ATTENTION: see note at the top of the file
def adjust_external_url(url: UnknownUrl, original_url: AbsoluteUrl | FeedUrl) -> AbsoluteUrl | None:
    if is_magnetic_url(url):
        return adjust_magnetic_url(url)

    return adjust_classic_url(url, original_url)


# ATTENTION: see note at the top of the file
def url_to_uid(url: AbsoluteUrl | FeedUrl) -> UrlUid:
    # The goal of this function is to detect URLs that most likely (99.(9)%) point to the same resource
    # It normalizes and simplifies a URL according to heuristics
    # I.e. there is a small possibility that two different URLs will be normalized to the same uid
    #
    # For example, http://example.com/ and http://example.com can return different data
    # In reality, it is mostly impossible and is a sign of bug or hacking on the side of third-party service
    # => We could remove a schema from the resulting uid
    #
    # Some normalization rules are based on personal taste,
    # for example, there are multiple ways to encode a URL or to normalize Unicode
    #
    # The rules are based on the next heuristics:
    #
    # - readability is better than technical representation
    # - it is ok to loss some corner URL forms, unless there is an explicit request to support them

    normalized_url = url.lower().strip()

    normalized_url = unquote(normalized_url)  # unquote all
    normalized_url = quote_plus(normalized_url)  # quoute with replacing spaces with pluses
    normalized_url = unquote(normalized_url)  # unquote all again, but keep pluses

    normalized_url = unicodedata.normalize("NFC", normalized_url)

    url_object = furl(normalized_url)

    url_object.scheme = None
    url_object.port = None
    url_object.fragment = None

    url_object.query.params = omdict(sorted(url_object.query.params.allitems()))

    # Attention: we must not remove username:password from the url
    #            because it will create a vector for hacking by accessing private news of other users

    path = str(url_object.path)

    while "//" in path:
        path = path.replace("//", "/")

    if path and path[-1] == "/":
        path = path[:-1]

    url_object.path = path

    # unquote again because furl will quote all parts of the url
    resulted_url = unquote(str(url_object))

    # furl adds // at the beginning of the url in some cases
    if resulted_url.startswith("//"):
        resulted_url = resulted_url[2:]

    return UrlUid(resulted_url)


# ATTENTION: see note at the top of the file
def url_to_source_uid(url: AbsoluteUrl | FeedUrl) -> SourceUid:
    # Because some portals (Reddit, ArXiv) provide customizable feed URLs,
    # we could see the same news entry in different feeds
    # => we should track the entry's source not by feed but by the portal
    # that will help us to ensure the entry's uniqueness.

    normalized_url = unicodedata.normalize("NFC", url).lower().strip()

    url_object = furl(normalized_url)

    domain = url_object.host

    # TODO: move rules to settings

    if domain.startswith("www."):
        domain = domain[4:]

    if domain.endswith(".reddit.com"):
        # xxx.reddit.com domains are just the old GUI version of reddit.com, or API, or old RSS urls
        domain = "reddit.com"

    assert isinstance(domain, str)

    return SourceUid(domain)


def url_has_extension(url: AbsoluteUrl, expected_extensions: list[str]) -> bool:
    f_url = furl(url)

    if not f_url.path.segments:
        return "" in expected_extensions

    last_segment = f_url.path.segments[-1]

    if "." not in last_segment:
        return "" in expected_extensions

    extension = last_segment.rsplit(".")[-1].strip()

    return f".{extension}" in expected_extensions


def filter_out_duplicated_urls(urls: Iterable[AbsoluteUrl]) -> list[AbsoluteUrl]:
    seen = set()

    result = []

    for url in urls:
        uid = url_to_uid(url)

        if uid in seen:
            continue

        seen.add(uid)
        result.append(url)

    return result


def get_parent_url(url: AbsoluteUrl | FeedUrl) -> AbsoluteUrl | None:
    f_url = furl(url)

    if not f_url.path.segments or f_url.path == "/":
        return None

    f_url.remove(query_params=True, fragment=True)

    if f_url.path.segments[-1] == "":
        f_url.path.segments = f_url.path.segments[:-1]
    else:
        f_url.path.segments[-1] = ""

    return normalize_classic_unknown_url(UnknownUrl(str(f_url)))


def to_feed_url(url: AbsoluteUrl) -> FeedUrl:
    f_url = furl(url)

    f_url.fragment = None

    return FeedUrl(str(f_url))
