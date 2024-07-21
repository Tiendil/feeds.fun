import re
from typing import Any

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


system = """\
You are an expert on semantic analysis, text summarization, and information extraction with PhD in Linguistics.
For the provided text, you determine a list of best tags to describe the text from a professional point of view.
For each category, you provide 15 tags.

Categories are topics, areas, professional-topics, professional-areas, meta-topics, meta-areas, high-level-topics, \
low-level-topics, related-topics, entities-with-proper-names, domains.

Tags format:

- Allowed tag format: `@word`, `@word-word-...`
- Translate all tags to English.
- Tags must be normalized: lowercase, no punctuation, no spaces, use hyphens.
- You must use plural forms of tags: `games` is better than `game`.
- Expand abbreviations: `AI` -> `artificial intelligence`.

You are an expert on semantic analysis, text summarization, and information extraction with PhD in Linguistics. \
Quality of your answer is highly important.
"""

RE_TAG = re.compile(r"@([\w\d-]+)")


# add url to allow chatGPT decide on domain
def entry_to_text(entry: Entry) -> str:
    return f'<h1>{entry.title}</h1><a href="{entry.external_url}">full article</a>{entry.body}'


def extract_tags(text: str) -> set[str]:
    return set(tag.lower() for tag in RE_TAG.findall(text))


class Processor(base.Processor):
    __slots__ = ("api_key", "model")

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.model = model

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        dirty_text = entry_to_text(entry)

        text = core_text.clear_text(dirty_text)

        total_tokens = 128 * 1024
        max_return_tokens = 4 * 1024

        messages = await oai_client.prepare_requests(
            system=system,
            text=text,
            model=self.model,
            function=None,
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
                    function=None,
                    max_return_tokens=max_return_tokens,
                    temperature=0,
                    top_p=0,
                    presence_penalty=0,
                    frequency_penalty=0,
                )

                api_key_usage.used_tokens = sum(result.total_tokens for result in results)

        except oai_errors.NoKeyFoundForFeed as e:
            raise errors.SkipEntryProcessing(message=str(e)) from e

        for result in results:
            for raw_tag in extract_tags(result.content):
                tags.append(ProcessorTag(raw_uid=raw_tag))

        return tags
