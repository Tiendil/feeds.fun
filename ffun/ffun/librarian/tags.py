
from slugify import slugify


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
                   regex_pattern=None,
                   lowercase=True,
                   replacements=(),
                   allow_unicode=False)


def normalize_tags(tags: set[str]) -> set[str]:
    return {normalize_tag(tag) for tag in tags}
