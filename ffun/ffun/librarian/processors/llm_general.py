from typing import Any
import asyncio
import importlib

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
from ffun.llms_framework.entities import LLMConfiguration, ChatRequest, ChatResponse, APIKeyUsage
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.providers import llm_providers
from ffun.llms_framework.domain import call_llm, search_for_api_key

logger = logging.get_module_logger()


# TODO: tests
class Processor(base.Processor):
    __slots__ = ("llm_config", "llm_provider", "entry_template", "text_cleaner", "tag_extractor")

    def __init__(self,
                 llm_config: LLMConfiguration,
                 entry_template: str,
                 text_cleaner: str,
                 tag_extractor: str,
                 **kwargs: Any):
        super().__init__(**kwargs)
        self.llm_config = llm_config
        self.llm_provider = llm_providers.get(llm_config.provider).provider
        self.entry_template = entry_template

        cleaner_module, cleaner_function = text_cleaner.rsplit(".", 1)
        self.text_cleaner = getattr(importlib.import_module(cleaner_module), cleaner_function)

        extractor_module, extractor_function = tag_extractor.rsplit(".", 1)
        self.tag_extractor = getattr(importlib.import_module(extractor_module), extractor_function)

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        dirty_text = self.entry_template.format(entry=entry)

        cleaned_text = self.text_cleaner(dirty_text)

        requests = self.llm_provider.prepare_requests(self.llm_config, cleaned_text)

        api_key_usage = await search_for_api_key(llm=self.llm_provider,
                                                 llm_config=self.llm_config,
                                                 entry=entry,
                                                 requests=requests)

        try:
            responses = await call_llm(llm=self.llm_provider,
                                       llm_config=self.llm_config,
                                       api_key_usage=api_key_usage,
                                       requests=requests)
        except llmsf_errors.NoKeyFoundForFeed as e:
            raise errors.SkipEntryProcessing(message=str(e)) from e

        return self.extract_tags(responses)

    def extract_tags(self, responses: list[ChatResponse]) -> list[ProcessorTag]:
        raw_tags = set()
        tags: list[ProcessorTag] = []

        for response in responses:
            raw_tags.update(self.tag_extractor(response.content))

        for raw_tag in raw_tags:
            tags.append(ProcessorTag(raw_uid=raw_tag))

        return tags
