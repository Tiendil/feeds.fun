import re

from bs4 import BeautifulSoup, Tag


def clear_nothing(text: str) -> str:
    return text


def clear_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")

    for tag in soup(["script", "style", "meta", "iframe", "img"]):
        tag.decompose()

    for tag in soup():

        if not isinstance(tag, Tag):
            continue

        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "a", "p", "li", "ul", "ol"}:
            continue

        tag.unwrap()

    simplified_html = str(soup)

    # remove borken surrogate unicode characters
    unicoded_html = simplified_html.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")

    cleaned_text = re.sub(r"\s+", " ", unicoded_html)

    return cleaned_text.strip()
