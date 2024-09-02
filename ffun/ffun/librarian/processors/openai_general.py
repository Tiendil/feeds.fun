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


RE_TAG = re.compile(r"@([\w\d-]+)")

# add url to allow chatGPT decide on domain
def entry_to_text(entry: Entry) -> str:
    return f'<h1>{entry.title}</h1><a href="{entry.external_url}">full article</a>{entry.body}'


def extract_raw_tags(text: str) -> set[str]:
    return set(tag.lower() for tag in RE_TAG.findall(text))


class Processor(base.Processor):
    __slots__ = ("llm_config",)

    def __init__(self, llm_config: LLMConfiguration, **kwargs: Any):
        super().__init__(**kwargs)
        self.llm_config = llm_config

    # TODO: tests
    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        dirty_text = entry_to_text(entry)

        text = core_text.clear_text(dirty_text)

        requests = provider.prepare_requests(self.llm_config, text)

        # TODO: move the code bellow into a separate function?
        #       maybe in https://github.com/Tiendil/feeds.fun/issues/245

        reserved_tokens = len(requests) * provider.max_context_size_for_model(self.llm_config)

        select_key_context = SelectKeyContext(feed_id=entry.feed_id,
                                              entry_age=entry.age,
                                              reserved_tokens=reserved_tokens)

        api_key_usage = await choose_api_key(select_key_context)

        try:
            async with use_api_key(api_key_usage):
                tasks = [provider.chat_request(self.llm_config,
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
