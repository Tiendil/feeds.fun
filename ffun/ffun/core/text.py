import re

from bs4 import BeautifulSoup


def clear_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")

    for tag in soup(["script", "style", "meta", "iframe", "img"]):
        tag.decompose()

    for tag in soup():
        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "a", "p", "li", "ul", "ol"}:
            continue

        tag.unwrap()

    simplified_html = str(soup)

    cleaned_text = re.sub(r"\s+", " ", simplified_html)

    return cleaned_text
