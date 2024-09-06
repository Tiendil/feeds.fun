import importlib
from typing import Any

from ffun.core import logging
from ffun.librarian import errors
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.domain import call_llm, search_for_api_key
from ffun.llms_framework.entities import ChatResponse, LLMConfiguration, Provider
from ffun.llms_framework.providers import llm_providers
from ffun.ontology.entities import ProcessorTag

logger = logging.get_module_logger()


# TODO: tests
class Processor(base.Processor):
    __slots__ = (
        "llm_config",
        "llm_provider",
        "entry_template",
        "text_cleaner",
        "tag_extractor",
        "collections_api_key",
        "general_api_key",
    )

    def __init__(  # noqa
        self,
            llm_provider: Provider,
        llm_config: LLMConfiguration,
        entry_template: str,
        text_cleaner: str,
        tag_extractor: str,
        collections_api_key: str | None,
        general_api_key: str | None,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.llm_config = llm_config
        self.llm_provider = llm_providers.get(llm_provider).provider
        self.entry_template = entry_template

        cleaner_module, cleaner_function = text_cleaner.rsplit(".", 1)
        self.text_cleaner = getattr(importlib.import_module(cleaner_module), cleaner_function)

        extractor_module, extractor_function = tag_extractor.rsplit(".", 1)
        self.tag_extractor = getattr(importlib.import_module(extractor_module), extractor_function)

        self.collections_api_key = collections_api_key
        self.general_api_key = general_api_key

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        dirty_text = self.entry_template.format(entry=entry)

        cleaned_text = self.text_cleaner(dirty_text)

        requests = self.llm_provider.prepare_requests(self.llm_config, cleaned_text)

        # TODO: too many agruments
        api_key_usage = await search_for_api_key(
            llm_config=self.llm_config,
            entry=entry,
            requests=requests,
            collections_api_key=self.collections_api_key,
            general_api_key=self.general_api_key,
        )

        if api_key_usage is None:
            raise errors.SkipEntryProcessing()

        responses = await call_llm(llm_config=self.llm_config, api_key_usage=api_key_usage, requests=requests)

        return self.extract_tags(responses)

    def extract_tags(self, responses: list[ChatResponse]) -> list[ProcessorTag]:
        raw_tags = set()
        tags: list[ProcessorTag] = []

        for response in responses:
            raw_tags.update(self.tag_extractor(response.response_content()))

        for raw_tag in raw_tags:
            tags.append(ProcessorTag(raw_uid=raw_tag))

        return tags
