import re
from typing import Any
import asyncio

from ffun.core import logging
from ffun.core import text as core_text
from ffun.librarian import errors
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag
from ffun.openai import client as oai_client
from ffun.openai import errors as oai_errors
from ffun.openai.entities import SelectKeyContext
from ffun.openai.keys_rotator import choose_api_key, use_api_key
from ffun.llms_framework.entities import LLMConfiguration
from ffun.llms_framework.provider_interface import provider

logger = logging.get_module_logger()


system = """\
You are an expert on semantic analysis, text summarization, and information extraction \
with PhD in Ontology-Driven Information Extraction.
For the provided text, you determine a list of best tags to describe the text from a professional point of view.
For each category, you provide 15 tags.

Categories are:

- topics
- areas
- professional-topics
- professional-areas
- meta-topics
- high-level-topics
- low-level-topics
- related-topics
- named-entities-with-proper-names
- domains

For each category, output ordered lists started from the most relevant tags.

1. tag with relevance > 95%: @tag-1
2. tag with relevance > 95%: @tag-2
3. tag with relevance > 95%: @tag-3
4. tag with relevance > 95%: @tag-4
5. tag with relevance > 95%: @tag-5
6. tag with relevance > 95%: @tag-6
7. tag with relevance > 95%: @tag-7
8. tag with relevance > 95%: @tag-8
9. tag with relevance > 95%: @tag-9
10. tag with relevance > 95%: @tag-10
11. tag with relevance > 95%: @tag-11
12. tag with relevance > 95%: @tag-12
13. tag with relevance > 95%: @tag-13
14. tag with relevance > 95%: @tag-14
15. tag with relevance > 95%: @tag-15

Tags format:

- Allowed tag format: `@word`, `@word-word-...`, `@word-number-...`,
- Translate all tags to English.
- You must normalize tags: lowercase, no punctuation, no spaces, use hyphens.
- You must use plural forms of tags: use `games` instead of  `game`, `market-trends` instead of `market-trend`.
- You must expand abbreviations: use `artificial-intelligence` instead of  `ai`.

Remember:

- You are an expert on semantic analysis, text summarization, and information extraction with PhD in Linguistics.
- The quality of your answer is critical.
- Each tag must be unique.
- I'll give you 10$ for each correct tag.
"""

RE_TAG = re.compile(r"@([\w\d-]+)")


# TODO: move to configs somewhere
llm_config = LLMConfiguration(
    model="gpt-4o-mini-2024-07-18",
    system=system,
    max_return_tokens=4 * 1024,
    text_parts_intersection=100,
    additional_tokens_per_message=10,
    temperature=0,
    top_p=0,
    presence_penalty=0,
    frequency_penalty=0)


# add url to allow chatGPT decide on domain
def entry_to_text(entry: Entry) -> str:
    return f'<h1>{entry.title}</h1><a href="{entry.external_url}">full article</a>{entry.body}'


def extract_raw_tags(text: str) -> set[str]:
    return set(tag.lower() for tag in RE_TAG.findall(text))


class Processor(base.Processor):
    __slots__ = ("api_key", "model")

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.model = model

    # TODO: tests
    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        dirty_text = entry_to_text(entry)

        text = core_text.clear_text(dirty_text)

        requests = provider.prepare_requests(llm_config, text)

        # TODO: move the code bellow into a separate function?
        #       maybe in https://github.com/Tiendil/feeds.fun/issues/245

        reserved_tokens = len(requests) * provider.max_context_size_for_model(llm_config)

        select_key_context = SelectKeyContext(feed_id=entry.feed_id,
                                              entry_age=entry.age,
                                              reserved_tokens=reserved_tokens)

        api_key_usage = await choose_api_key(select_key_context)

        try:
            async with use_api_key(api_key_usage):
                tasks = [provider.chat_request(llm_config,
                                               api_key_usage.api_key,
                                               request)
                         for request in requests]

                responses = await asyncio.gather(*tasks)

                api_key_usage.used_tokens = sum(response.total_tokens for response in responses)

        except oai_errors.NoKeyFoundForFeed as e:
            raise errors.SkipEntryProcessing(message=str(e)) from e

        for response in responses:
            for raw_tag in extract_raw_tags(response.content):
                tags.append(ProcessorTag(raw_uid=raw_tag))

        return tags
