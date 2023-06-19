
import re

from slugify import slugify

DISALLOWED_CHARS_PATTERN = re.compile(r'[^-a-zA-Z0-9]+')


_replacements = {
    '#': '-sharp-',  # c# -> c-sharp
    '+': '-plus-',  # c++ -> c-plus-plus
    '.': '-dot-',  # .net -> dot-net
}


def build_uid_for_raw_tag(tag: str) -> str:
    for substring, replacement in _replacements.items():
        tag = tag.replace(substring, replacement)

    return slugify(tag,
                   entities=True,
                   decimal=True,
                   hexadecimal=True,
                   max_length=0,
                   word_boundary=False,
                   save_order=True,
                   separator='-',
                   stopwords=(),
                   regex_pattern=DISALLOWED_CHARS_PATTERN,
                   lowercase=True,
                   replacements=(),
                   allow_unicode=False)
