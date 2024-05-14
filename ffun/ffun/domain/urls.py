import re
import unicodedata
from urllib.parse import quote_plus, unquote

from furl import furl
from orderedmultidict import omdict

RE_SCHEMA = re.compile(r"^(\w+):")


# TODO: maybe switch to https://github.com/tktech/can_ada


# TODO: add tests
# is required for correct parsing by furl
# will be removed before returning result
def _fake_schema_for_url(url: str) -> str:
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


def normalize_classic_url(url: str, original_url: str) -> str:
    url = _fake_schema_for_url(url)
    original_url = _fake_schema_for_url(original_url)

    external_url = furl(url)

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


def normalize_external_url(url: str, original_url: str) -> str:
    if is_magnetic_url(url):
        return normalize_magnetic_url(url)

    return normalize_classic_url(url, original_url)


def url_to_uid(url: str) -> str:
    # The goal of this function is to detect urls that most likely (99.(9)%) point to the same resource
    # It normalizes and simplifies an url according to heuristics
    # I.e. there is a small possibility that two different urls will be normalized to the same uid
    #
    # For example, http://example.com/ and http://example.com can return different data
    # In reality it is mostly imposible and is a signe of bug or hacking on the side of third-party service
    # => we could remove schema from the resulted uid
    #
    # Some normalization rules are based on personal taste,
    # for example, there are multiple ways to encode a url or to normalize unicode
    #
    # The rules are based on the next heuristics:
    #
    # - readability are better than technical representation
    # - it is ok to loss some corner urls forms, unless there will be an explicit request to support them

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
