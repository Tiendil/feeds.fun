import re
import unicodedata
from urllib.parse import quote_plus, unquote

from furl import furl
from orderedmultidict import omdict

from ffun.core import logging
from ffun.domain import errors
from ffun.domain.entities import AbsoluteUrl, SourceUid, UnknownUrl, UrlUid

logger = logging.get_module_logger()


# ATTENTION: in case of modification, you MUST check:
#            - that the logic of dependent functions is not broken
#            - that the UIDs generation is not changed (check on backup)
#            - in case UIDs generation is changed, you MUST update all affected entities

# TODO: there a lot of refactoring done, check if UIDs update is required
# TODO: test manually


RE_SCHEMA = re.compile(r"^(\w+):")


def is_expected_furl_error(error: Exception) -> bool:
    message = str(error)

    if "Invalid port" in message:
        return True

    return False


# ATTENTION: see note at the top of the file
def normalize_classic_unknown_url(url: UnknownUrl) -> AbsoluteUrl | None:  # noqa: CCR001
    url = UnknownUrl(url.strip())

    # check if url is parsable
    try:
        f_url = furl(url)
    except ValueError as e:
        if is_expected_furl_error(e):
            return None

        raise

    f_url.remove(fragment=True)

    if url.startswith("//"):
        return AbsoluteUrl(str(f_url))

    if url.startswith("./") or url.startswith("../"):
        return None

    if RE_SCHEMA.match(url):
        return AbsoluteUrl(str(f_url))

    # we should have proper domains
    # TODO: refactor to some ideomatic way
    if "." not in url.split("/")[0]:
        return None

    f_url = furl(f"//{url}")
    f_url.remove(fragment=True)

    return AbsoluteUrl(str(f_url))


# ATTENTION: see note at the top of the file
def is_full_url(url: UnknownUrl) -> bool:
    return normalize_classic_unknown_url(url) is not None


def str_to_absolute_url(url: str) -> AbsoluteUrl:
    """Convert or raise Exception

    It is shortcut method mostly for tests.
    Use `normalize_classic_unknown_url` in the production code.
    """
    absolute_url = normalize_classic_unknown_url(UnknownUrl(url))

    if absolute_url is None:
        raise errors.UrlIsNotAbsolute(url=url)

    return absolute_url


# ATTENTION: see note at the top of the file
def is_absolute_url(url: str) -> bool:
    """Check if the URL is absolute and is normalized"""
    return normalize_classic_unknown_url(UnknownUrl(url)) == url


# ATTENTION: see note at the top of the file
def adjust_classic_full_url(url: UnknownUrl, original_url: AbsoluteUrl) -> AbsoluteUrl | None:
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
def adjust_classic_relative_url(url: UnknownUrl, original_url: AbsoluteUrl) -> AbsoluteUrl | None:
    f_url = furl(original_url)

    f_url.remove(query_params=True, fragment=True)

    try:
        f_url.join(url)
    except ValueError as e:
        if is_expected_furl_error(e):
            return None

        raise

    return AbsoluteUrl(str(f_url))


# ATTENTION: see note at the top of the file
def adjust_classic_url(url: UnknownUrl, original_url: AbsoluteUrl) -> AbsoluteUrl | None:
    if is_full_url(url):
        return adjust_classic_full_url(url, original_url)

    return adjust_classic_relative_url(url, original_url)


def is_magnetic_url(url: UnknownUrl) -> bool:
    return url.startswith("magnet:")


def adjust_magnetic_url(url: UnknownUrl) -> AbsoluteUrl:
    return AbsoluteUrl(url)


# ATTENTION: see note at the top of the file
def adjust_external_url(url: UnknownUrl, original_url: AbsoluteUrl) -> AbsoluteUrl | None:
    if is_magnetic_url(url):
        return adjust_magnetic_url(url)

    return adjust_classic_url(url, original_url)


# ATTENTION: see note at the top of the file
def url_to_uid(url: AbsoluteUrl) -> UrlUid:
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
def url_to_source_uid(url: AbsoluteUrl) -> SourceUid:
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

    last_segment = f_url.path.segments[-1]

    if '.' not in last_segment:
        return '' in expected_extensions

    extension = last_segment.rsplit(".")[-1].strip()

    return f".{extension}" in expected_extensions


def filter_out_duplicated_urls(urls: list[AbsoluteUrl]) -> list[AbsoluteUrl]:
    seen = set()

    result = []

    for url in urls:
        uid = url_to_uid(url)

        if uid in seen:
            continue

        seen.add(uid)
        result.append(url)

    return result
