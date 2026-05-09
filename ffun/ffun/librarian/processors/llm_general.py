from typing import Any, Sequence

from ffun.core import logging
from ffun.domain.entities import LLMTokens
from ffun.librarian import errors
from ffun.librarian.entities import TagsExtractor, TextCleaner
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.domain import (
    call_llm,
    collection_api_key_usage,
    cut_text_to_max_tokens,
    general_api_key_usage,
    search_for_user_api_key,
)
from ffun.llms_framework.entities import (
    APIKeyUsage,
    ChatRequest,
    ChatResponse,
    LLMApiKeyType,
    LLMCollectionApiKey,
    LLMConfiguration,
    LLMGeneralApiKey,
    LLMProvider,
)
from ffun.llms_framework.providers import llm_providers
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagCategory

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
        "max_tokens_per_entry",
        "text_parts_intersection",
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
        max_tokens_per_entry: LLMTokens,
        text_parts_intersection: int,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)  # type: ignore
        self.llm_config = llm_config
        self.llm_provider = llm_providers.get(llm_provider).provider
        self.entry_template = entry_template
        self.text_cleaner = text_cleaner
        self.tag_extractor = tag_extractor

        self.collections_api_key = collections_api_key
        self.general_api_key = general_api_key

        self.max_tokens_per_entry = max_tokens_per_entry
        self.text_parts_intersection = text_parts_intersection

    def _text_to_process(self, entry: Entry) -> str:
        dirty_text = self.entry_template.format(entry=entry)

        cleaned_text = self.text_cleaner(dirty_text)

        cut_text = cut_text_to_max_tokens(
            llm=self.llm_provider, llm_config=self.llm_config, text=cleaned_text, max_tokens=self.max_tokens_per_entry
        )

        return cut_text

    async def _api_key_usage(
        self, entry: Entry, requests: Sequence[ChatRequest], context: base.ProcessorContext
    ) -> APIKeyUsage | None:
        match context.llm_api_key_type:
            case LLMApiKeyType.general if self.general_api_key is not None:
                return general_api_key_usage(
                    llm=self.llm_provider,
                    llm_config=self.llm_config,
                    api_key=self.general_api_key,
                    requests=requests,
                )

            case LLMApiKeyType.collection if self.collections_api_key is not None:
                return collection_api_key_usage(
                    llm=self.llm_provider,
                    llm_config=self.llm_config,
                    api_key=self.collections_api_key,
                    requests=requests,
                )

            case LLMApiKeyType.user:
                return await search_for_user_api_key(
                    llm=self.llm_provider,
                    llm_config=self.llm_config,
                    entry=entry,
                    requests=requests,
                )

            case _:
                return None

    async def process(self, entry: Entry, context: base.ProcessorContext) -> list[RawTag]:

        cleaned_text = self._text_to_process(entry)

        requests = self.llm_provider.prepare_requests(self.llm_config, cleaned_text, self.text_parts_intersection)

        api_key_usage = await self._api_key_usage(entry=entry, requests=requests, context=context)

        if api_key_usage is None:
            raise errors.SkipEntryProcessing(message="no api key found")

        try:
            responses = await call_llm(
                llm=self.llm_provider, llm_config=self.llm_config, api_key_usage=api_key_usage, requests=requests
            )
        except llmsf_errors.TemporaryError as e:
            raise errors.TemporaryErrorInProcessor(message=str(e)) from e

        return self.extract_tags(responses)

    def extract_tags(self, responses: Sequence[ChatResponse]) -> list[RawTag]:
        raw_tags = set()
        tags: list[RawTag] = []

        for response in responses:
            raw_tags.update(self.tag_extractor(response.response_content()))

        for raw_tag in raw_tags:
            tags.append(
                RawTag(
                    raw_uid=raw_tag,
                    categories={TagCategory.free_form},
                )
            )

        return tags
