from typing import Any, Sequence

from ffun.core import logging
from ffun.librarian import errors
from ffun.librarian.entities import TagsExtractor, TextCleaner
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.llms_framework.domain import call_llm, search_for_api_key
from ffun.llms_framework.entities import (
    ChatResponse,
    LLMCollectionApiKey,
    LLMConfiguration,
    LLMGeneralApiKey,
    LLMProvider,
)
from ffun.llms_framework.providers import llm_providers
from ffun.ontology.entities import ProcessorTag

logger = logging.get_module_logger()


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
        llm_provider: LLMProvider,
        llm_config: LLMConfiguration,
        entry_template: str,
        text_cleaner: TextCleaner,
        tag_extractor: TagsExtractor,
        collections_api_key: LLMCollectionApiKey | None,
        general_api_key: LLMGeneralApiKey | None,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.llm_config = llm_config
        self.llm_provider = llm_providers.get(llm_provider).provider
        self.entry_template = entry_template
        self.text_cleaner = text_cleaner
        self.tag_extractor = tag_extractor

        self.collections_api_key = collections_api_key
        self.general_api_key = general_api_key

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        dirty_text = self.entry_template.format(entry=entry)

        cleaned_text = self.text_cleaner(dirty_text)

        requests = self.llm_provider.prepare_requests(self.llm_config, cleaned_text)

        api_key_usage = await search_for_api_key(
            llm=self.llm_provider,
            llm_config=self.llm_config,
            entry=entry,
            requests=requests,
            collections_api_key=self.collections_api_key,
            general_api_key=self.general_api_key,
        )

        if api_key_usage is None:
            raise errors.SkipEntryProcessing(message="no api key found")

        responses = await call_llm(
            llm=self.llm_provider, llm_config=self.llm_config, api_key_usage=api_key_usage, requests=requests
        )

        return self.extract_tags(responses)

    def extract_tags(self, responses: Sequence[ChatResponse]) -> list[ProcessorTag]:
        raw_tags = set()
        tags: list[ProcessorTag] = []

        for response in responses:
            raw_tags.update(self.tag_extractor(response.response_content()))

        for raw_tag in raw_tags:
            tags.append(ProcessorTag(raw_uid=raw_tag))

        return tags
