import json
from typing import Any

from ffun.core import json as core_json
from ffun.core import logging
from ffun.core import text as core_text
from ffun.librarian import errors
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag
from ffun.openai import client as oai_client
from ffun.openai import errors as oai_errors
from ffun.openai.keys_rotator import api_key_for_feed_entry

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
                            },
                        },
                    },
                },
            }
        },
    },
}


# add url to allow chatGPT decide on domain
def entry_to_text(entry: Entry) -> str:
    return f'<h1>{entry.title}</h1><a href="{entry.external_url}">full article</a>{entry.body}'


trash_system_tags = {"topic", "topics", "category", "meta-category", "five-most-related-tags-for-text"}


def extract_tags(text: str) -> set[str]:
    try:
        data = core_json.loads_with_fix(text)

        # there is no point in following format
        # because it can be broken in all possible ways
        # for example, ChatGPT may return additional fields
        tags = core_json.extract_tags_from_random_json(data)
    except json.decoder.JSONDecodeError:
        tags = core_json.extract_tags_from_invalid_json(text)

    return tags - trash_system_tags


class Processor(base.Processor):
    __slots__ = ("api_key", "model")

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.model = model

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        dirty_text = entry_to_text(entry)

        text = core_text.clear_text(dirty_text)

        total_tokens = 16 * 1024
        max_return_tokens = 4 * 1024

        messages = await oai_client.prepare_requests(
            system=system,
            text=text,
            model=self.model,
            function=function,
            total_tokens=total_tokens,
            max_return_tokens=max_return_tokens,
        )

        try:
            async with api_key_for_feed_entry(
                entry.feed_id, entry_age=entry.age, reserved_tokens=len(messages) * total_tokens
            ) as api_key_usage:
                results = await oai_client.multiple_requests(
                    api_key=api_key_usage.api_key,
                    model=self.model,
                    messages=messages,
                    function=function,
                    max_return_tokens=max_return_tokens,
                    temperature=1,
                    top_p=0,
                    presence_penalty=1,
                    frequency_penalty=0,
                )

                api_key_usage.used_tokens = sum(result.total_tokens for result in results)

        except oai_errors.NoKeyFoundForFeed as e:
            raise errors.SkipEntryProcessing(message=str(e)) from e

        for result in results:
            for raw_tag in extract_tags(result.content):
                tags.append(ProcessorTag(raw_uid=raw_tag))

        return tags
