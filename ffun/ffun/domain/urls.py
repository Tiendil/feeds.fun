import re
import unicodedata
from urllib.parse import quote_plus, unquote

from furl import furl
from orderedmultidict import omdict

from ffun.core import logging

logger = logging.get_module_logger()


RE_SCHEMA = re.compile(r"^(\w+):")


# TODO: maybe switch to https://github.com/tktech/can_ada


# TODO: add tests
# is required for correct parsing by furl
# will be removed before returning result
def _fake_schema_for_url(url: str) -> str:
    url = url.strip()

    if url.startswith("//"):
        return url

    if RE_SCHEMA.match(url):
        return url

    # TODO: this logic is required only for normalize_classic_url and has wrong behavior for top-level domains
    #       like localhost or any other one-part domain that user will define locally
    if "." not in url.split("/")[0]:
        # if there is no domain, just return the url
        return url

    return f"//{url}"


def normalize_classic_url(url: str, original_url: str) -> str | None:
    url = _fake_schema_for_url(url)
    original_url = _fake_schema_for_url(original_url)

    try:
        external_url = furl(url)
    except ValueError as e:
        error = str(e)

        logger.warning("invalid_url", url=url, error=error)

        if "Invalid port" in error:
            return None

        raise

    f_original_url = furl(original_url)

    if not external_url.scheme:
        external_url.set(scheme=f_original_url.scheme)

    if not external_url.netloc:
        external_url.set(netloc=f_original_url.netloc)

    result_url = str(external_url)

    if result_url.startswith("//"):
        result_url = result_url[2:]

    return result_url


def is_magnetic_url(url: str) -> bool:
    return url.startswith("magnet:")


def normalize_magnetic_url(url: str) -> str:
    return url


def normalize_external_url(url: str, original_url: str) -> str | None:
    if is_magnetic_url(url):
        return normalize_magnetic_url(url)

    return normalize_classic_url(url, original_url)


def url_to_uid(url: str) -> str:
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

    normalized_url = _fake_schema_for_url(url.lower().strip())

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

    return resulted_url


def url_to_source_uid(url: str) -> str:
    # Because some portals (Reddit, ArXiv) provide customizable feed URLs,
    # we could see the same news entry in different feeds
    # => we should track the entry's source not by feed but by the portal
    # that will help us to ensure the entry's uniqueness.

    normalized_url = unicodedata.normalize("NFC", url).lower().strip()

    normalized_url = _fake_schema_for_url(normalized_url)

    url_object = furl(normalized_url)

    domain = url_object.host

    # TODO: move rules to settings

    if domain.startswith("www."):
        domain = domain[4:]

    if domain.endswith(".reddit.com"):
        # xxx.reddit.com domains are just the old GUI version of reddit.com, or API, or old RSS urls
        domain = "reddit.com"

    assert isinstance(domain, str)

    return domain
