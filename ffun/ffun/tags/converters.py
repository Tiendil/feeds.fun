from slugify import slugify

from ffun.domain.entities import TagUid

_encode_replacements = {
    "#": "-sharp-",  # c# -> c-sharp
    "+": "-plus-",  # c++ -> c-plus-plus
    ".": "-dot-",  # .net -> dot-net, example.com -> example-dot-com
}


_decode_replacements = {v.strip("-"): k for k, v in _encode_replacements.items()}

constant_tag_parts = list(_encode_replacements.values())


def _encode_special_characters(tag: str) -> str:
    for substring, replacement in _encode_replacements.items():
        tag = tag.replace(substring, replacement)

    return tag


def _decode_special_characters(tag: str) -> str:
    parts = tag.split("-")
    parts = [part for part in parts if part]

    result = []
    can_add_dash = False

    for part in parts:
        if part not in _decode_replacements:
            if can_add_dash:
                result.append("-")

            can_add_dash = True
            result.append(part)
            continue

        can_add_dash = False
        result.append(_decode_replacements[part])

    return "".join(result)


def normalize(tag: str, allow_unicode: bool) -> TagUid:
    tag = tag.lower()

    tag = _encode_special_characters(tag)

    # Note: with allow_unicode True slugify normalizes unicode to NFKC
    #       if in the future we'll decide to change library for slugification
    #       we should either ensure that behavior or renormalize tags in the database.
    return TagUid(
        slugify(
            tag,
            entities=True,
            decimal=True,
            hexadecimal=True,
            max_length=0,
            word_boundary=False,
            save_order=True,
            separator="-",
            stopwords=(),
            regex_pattern=None,
            lowercase=True,
            replacements=(),
            allow_unicode=allow_unicode,
        )
    )


def verbose(tag: str) -> str:
    return _decode_special_characters(tag)
