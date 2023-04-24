
import re

from slugify import slugify

# extended regex from slugify for allow_unicode=False case
# changes:
# . — dot is required for tags with domain names
DISALLOWED_CHARS_PATTERN = re.compile(r'[^-a-zA-Z0-9.]+')


def normalize_tag(tag: str) -> str:
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


def normalize_tags(tags: set[str]) -> set[str]:
    return {normalize_tag(tag) for tag in tags}
