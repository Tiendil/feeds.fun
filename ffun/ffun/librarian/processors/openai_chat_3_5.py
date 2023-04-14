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

from .. import openai_client as oc
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

Tags are only in English. Normalize tags and output them as JSON.\
'''


# add url to allow chatGPT decide on domain
def entry_to_text(entry: Entry) -> str:
    return f'<h1>{entry.title}</h1><a href="{entry.external_url}">full article</a>{entry.body}'


def clear_text(text: str) -> str:
    soup = BeautifulSoup(text, 'html.parser')

    for tag in soup(['script', 'style', 'meta', 'iframe', 'img']):
        tag.decompose()

    for tag in soup():
        if tag.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'p', 'li', 'ul', 'ol'}:
            continue

        tag.unwrap()

    simplified_html = str(soup)

    cleaned_text = re.sub(r'\s+', ' ', simplified_html)

    return cleaned_text


def _extract_tags(data: Any) -> set[str]:
    if not data:
        # no tags if [], {}, ''
        return set()

    if isinstance(data, list):
        return set.union(*(_extract_tags(item) for item in data))

    if isinstance(data, dict):
        return set.union(*(_extract_tags(key)|_extract_tags(value) for key, value in data.items()))

    if isinstance(data, str):
        return {data}

    return set()


trash_system_tags = {'topics',
                     'meta-topics',
                     'high-level-topics',
                     'low-level-topics',
                     'related-topics',
                     'indirect-topics',
                     'mentions',
                     'indirect-mentions'}

# TODO: process errors
# TODO: try to fix broken JSON

def extract_tags_from_valid_json(text: str) -> set[str]:
    data = json.loads(text)
    tags = _extract_tags(data)
    return tags - trash_system_tags


def extract_tags_from_invalid_json(text: str) -> set[str]:
    logger.warning('Try to extract tags from an invalid JSON: %s', text)

    # search all strings, believing that
    parts = text.split('"')

    tags: set[str] = set()

    is_tag = False

    while parts:
        value = parts.pop(0)

        if is_tag:
            tags.add(value)

        is_tag = not is_tag

    logger.warning('Tags extracted: %s', tags)

    return tags


def extract_tags(text: str) -> set[str]:
    try:
        return extract_tags_from_valid_json(text)
    except json.decoder.JSONDecodeError:
        return extract_tags_from_invalid_json(text)


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> set[str]:
        dirty_text = entry_to_text(entry)

        text = clear_text(dirty_text)

        model = 'gpt-3.5-turbo'
        total_tokens = 4096
        max_return_tokens = 1024

        messages = await oc.prepare_requests(system=system,
                                             text=text,
                                             model=model,
                                             total_tokens=total_tokens,
                                             max_return_tokens=max_return_tokens)

        results = await oc.multiple_requests(model=model,
                                             messages=messages,
                                             max_return_tokens=max_return_tokens)

        tags = set()

        for result in results:
            tags |= extract_tags(result)

        return tags
