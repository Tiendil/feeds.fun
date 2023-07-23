import re

from slugify import slugify


DISALLOWED_CHARS_PATTERN = re.compile(r"[^-a-zA-Z0-9]+")


_encode_replacements = {
    "#": "-sharp-",  # c# -> c-sharp
    "+": "-plus-",  # c++ -> c-plus-plus
    ".": "-dot-",  # .net -> dot-net, example.com -> example-dot-com
}


_decode_replacements = {v: k for k, v in _encode_replacements.items()}


def _encode_special_characters(tag: str) -> str:
    for substring, replacement in _encode_replacements.items():
        tag = tag.replace(substring, replacement)

    return tag


def _decode_special_characters(tag: str) -> str:
    tag = f"-{tag}-"

    for substring, replacement in _decode_replacements.items():
        tag = tag.replace(substring, replacement)

    tag = tag.strip("-")

    return tag


def normalize(tag: str) -> str:
    tag = tag.lower()

    tag = _encode_special_characters(tag)

    return slugify(
        tag,
        entities=True,
        decimal=True,
        hexadecimal=True,
        max_length=0,
        word_boundary=False,
        save_order=True,
        separator="-",
        stopwords=(),
        regex_pattern=DISALLOWED_CHARS_PATTERN,  # type: ignore
        lowercase=True,
        replacements=(),
        allow_unicode=False,
    )


def verbose(tag: str) -> str:
    return _decode_special_characters(tag)
