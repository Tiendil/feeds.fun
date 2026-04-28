import re
from typing import cast

from bs4 import BeautifulSoup, Tag

_SEMANTIC_ATTRIBUTES = frozenset(
    {
        "alt",
        "aria-label",
        "cite",
        "datetime",
        "href",
        "lang",
        "longdesc",
        "poster",
        "src",
        "srcset",
        "title",
    }
)

_DECOMPOSED_TAG_NAMES = ("script", "style", "meta", "iframe")

_KEPT_TAG_NAMES = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "a", "p", "li", "ul", "ol", "img"})


def clear_nothing(text: str) -> str:
    return text


def _remove_non_semantic_attributes(tag: Tag) -> None:
    attributes = cast(dict[str, object], tag.attrs)

    for attribute in list(attributes):
        if attribute not in _SEMANTIC_ATTRIBUTES:
            del attributes[attribute]


def clear_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")

    decomposed_tags = cast(list[Tag], soup.find_all(_DECOMPOSED_TAG_NAMES))

    for decomposed_tag in decomposed_tags:
        decomposed_tag.decompose()

    tags = cast(list[object], soup.find_all())

    for tag in tags:

        if not isinstance(tag, Tag):
            continue

        _remove_non_semantic_attributes(tag)

        if tag.name in _KEPT_TAG_NAMES:
            continue

        tag.unwrap()

    simplified_html = str(soup)

    # remove broken surrogate Unicode characters
    unicoded_html = simplified_html.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")

    cleaned_text = re.sub(r"\s+", " ", unicoded_html)

    return cleaned_text.strip()
