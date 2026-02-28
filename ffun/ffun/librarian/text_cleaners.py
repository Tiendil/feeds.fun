import re
from typing import cast

from bs4 import BeautifulSoup, Tag


def clear_nothing(text: str) -> str:
    return text


def clear_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")

    decomposed_tags = cast(list[Tag], soup.find_all(["script", "style", "meta", "iframe", "img"]))

    for decomposed_tag in decomposed_tags:
        decomposed_tag.decompose()

    tags = cast(list[object], soup.find_all())

    for tag in tags:

        if not isinstance(tag, Tag):
            continue

        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "a", "p", "li", "ul", "ol"}:
            continue

        tag.unwrap()

    simplified_html = str(soup)

    # remove broken surrogate Unicode characters
    unicoded_html = simplified_html.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")

    cleaned_text = re.sub(r"\s+", " ", unicoded_html)

    return cleaned_text.strip()
