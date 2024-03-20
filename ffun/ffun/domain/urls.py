from furl import furl


# is required for correct parsing by furl
# will be removed before returning result
def _fake_schema_for_url(url: str) -> str:
    if "//" not in url and url[0] != "/" and ("." in url.split("/")[0]):
        return f"//{url}"

    return url


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
