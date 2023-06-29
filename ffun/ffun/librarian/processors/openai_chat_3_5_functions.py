import json
import re
import textwrap
from typing import Any

import typer
from ffun.core import json as core_json
from ffun.core import logging
from ffun.core import text as core_text
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag, TagCategory
from slugify import slugify

from .. import openai_client as oc
from . import base

logger = logging.get_module_logger()


system = (
    "You are an expert on text analysis. "
    "For provided text, you describe mentioned topics. "
    "You describe text from professional point of view. "
    "You fully describe text in multiple levels of abstraction. "
    "You MUST provide 100 topics for the text starting from the most relevant. "
    "All topics MUST be in English."
)


# ATTENTION: order of fields is important
function = {
    "name": "register_topics",
    "description": "Saves topics of the text.",
    "parameters": {
        "type": "object",
        "properties": {

            "topics": {
                "type": "array",
                "description": "list of topics",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                        },

                        "category": {
                            "type": "string",
                        },

                        "meta-category": {
                            "type": "string",
                        },

                        "five-most-related-tags-for-text": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            }
                        }
                    }
                }
            }
        }
    }
}


# add url to allow chatGPT decide on domain
def entry_to_text(entry: Entry) -> str:
    return f'<h1>{entry.title}</h1><a href="{entry.external_url}">full article</a>{entry.body}'


trash_system_tags = {'topic',
                     'category',
                     'meta-category',
                     'five-most-related-tags-for-text'}


def extract_tags_from_expected_format(data: Any) -> set[str]:
    tags = set()

    for topic in data['topics']:
        tags.add(topic['topic'])
        tags.add(topic['category'])
        tags.add(topic['meta-category'])
        tags.update(topic['five-most-related-tags-for-text'])

    return tags


def extract_tags(text: str) -> set[str]:
    try:
        data = core_json.loads_with_fix(text)

        try:
            tags = extract_tags_from_expected_format(data)
        except Exception:
            logger.exception('unexpected_json_format')
            tags = core_json.extract_tags_from_random_json(data)

    except json.decoder.JSONDecodeError:
        tags = core_json.extract_tags_from_invalid_json(text)

    return tags - trash_system_tags


class Processor(base.Processor):
    __slots__ = ('api_key',)

    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key

        # TODO: we need support multiple api keys
        oc.init(self.api_key)

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        dirty_text = entry_to_text(entry)

        text = core_text.clear_text(dirty_text)

        model = 'gpt-3.5-turbo-16k'
        total_tokens = 16 * 1024
        max_return_tokens = 4 * 1024

        # todo: add tokens from function
        messages = await oc.prepare_requests(system=system,
                                             text=text,
                                             model=model,
                                             function=function,
                                             total_tokens=total_tokens,
                                             max_return_tokens=max_return_tokens)

        # TODO: specify concreate model
        results = await oc.multiple_requests(model=model,
                                             messages=messages,
                                             function=function,
                                             max_return_tokens=max_return_tokens,
                                             temperature=1,
                                             top_p=0,
                                             presence_penalty=1,
                                             frequency_penalty=0)

        for result in results:
            for raw_tag in extract_tags(result):
                tags.append(ProcessorTag(raw_uid=raw_tag,
                                         name=raw_tag))

        return tags
