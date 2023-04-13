import json
import logging
import re
import textwrap
from typing import Any

import openai
import typer
from bs4 import BeautifulSoup
from ffun.library.entities import Entry
from slugify import slugify

from ..settings import settings
from . import base

logger = logging.getLogger(__name__)


openai.api_key = settings.openai.api_key


logger = logging.getLogger(__name__)


# TODO: "programming-language" vs "programming-languages".
# TODO: if we add specific tag, like "recident-evil-2", we should add more general tag like "recident-evil" too.


system = '''\
You are an expert on the analysis of text semantics.
For provided text, you determine a list of best tags to describe the text.
For each category, you provide 30 tags.

Categories are topics, meta-topics, high-level-topics, low-level-topics, related-topics, indirect-topics, mentions, indirect-mentions.

Normalize tags and output them as JSON.\
'''


def entry_to_text(entry: Entry) -> str:
    return f'title: {entry.title}\n\n{entry.text}'


def clear_text(text: str) -> str:
    soup = BeautifulSoup(text, 'html.parser')

    for tag in soup(['script', 'style', 'meta', 'iframe', 'img']):
        tag.decompose()

    for tag in soup():
        if tag.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'p', 'li', 'ul', 'ol'}:
            continue
        tag.unwrap()

    simplified_html = soup.get_text()

    cleaned_text = re.sub(r'\s+', ' ', simplified_html)

    return cleaned_text


def _extract_tags(data: Any) -> set[str]:
    if isinstance(data, list):
        return set.union(*(_extract_tags(item) for item in data))

    if isinstance(data, dict):
        return set.union(*(_extract_tags(key)|_extract_tags(value) for key, value in data.items()))

    if isinstance(data, str):
        return {data}

    return set()


# TODO: process errors
# TODO: try to fix broken JSON
def extract_tags(text: str) -> set[str]:
    data = json.loads(text)
    return _extract_tags(data)


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


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> set[str]:
        pass
