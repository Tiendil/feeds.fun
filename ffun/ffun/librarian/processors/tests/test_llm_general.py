import pytest

from ffun.librarian import errors
from ffun.librarian.processors.llm_general import Processor
from ffun.librarian.tag_extractors import dog_tags_extractor
from ffun.librarian.text_cleaners import clear_nothing
from ffun.library.entities import Entry
from ffun.llms_framework.entities import LLMApiKey, LLMConfiguration, LLMGeneralApiKey, LLMProvider, LLMTokens
from ffun.llms_framework.provider_interface import ChatResponseTest
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagCategory


class TestProcessor:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    @pytest.fixture  # type: ignore
    def llm_processor(self, llm_config: LLMConfiguration) -> Processor:
        return Processor(
            name="test-llm-processor",
            llm_provider=LLMProvider.test,
            llm_config=llm_config,
            entry_template="{entry.title} {entry.body}",
            text_cleaner=clear_nothing,
            tag_extractor=dog_tags_extractor,
            collections_api_key=None,
            general_api_key=None,
            max_tokens_per_entry=LLMTokens(1_000),
            text_parts_intersection=100,
        )

    def test_extract_tags(self, llm_processor: Processor) -> None:

        responses = [
            ChatResponseTest(
                content="@tag-1 @tag-2",
            ),
            ChatResponseTest(content="@tag-3 @tag-2"),
        ]

        tags = llm_processor.extract_tags(responses)

        tags.sort(key=lambda x: x.raw_uid)

        assert tags == [
            RawTag(raw_uid="tag-1", categories={TagCategory.free_form}),
            RawTag(raw_uid="tag-2", categories={TagCategory.free_form}),
            RawTag(raw_uid="tag-3", categories={TagCategory.free_form}),
        ]

    def test__text_to_process__formats_cleans_and_cuts(self, llm_processor: Processor, cataloged_entry: Entry) -> None:
        llm_processor.entry_template = "title={entry.title}; body={entry.body}"
        llm_processor.max_tokens_per_entry = LLMTokens(10)

        def text_cleaner(text: str) -> str:
            return text.upper()

        llm_processor.text_cleaner = text_cleaner

        entry = cataloged_entry.replace(title="hello", body="world")

        assert llm_processor._text_to_process(entry) == "TITLE=HELL"

    @pytest.mark.asyncio
    async def test_process__no_api_key_found(self, llm_processor: Processor, cataloged_entry: Entry) -> None:
        with pytest.raises(errors.SkipEntryProcessing):
            await llm_processor.process(cataloged_entry)

    @pytest.mark.asyncio
    async def test_process__has_api_key_found(
        self, llm_processor: Processor, cataloged_entry: Entry, fake_llm_api_key: LLMApiKey
    ) -> None:

        entry = cataloged_entry.replace(title="@tag-1 @tag-2", body="@tag-3 @tag-2")

        llm_processor.general_api_key = LLMGeneralApiKey(fake_llm_api_key)

        tags = await llm_processor.process(entry)

        tags.sort(key=lambda x: x.raw_uid)

        assert tags == [
            RawTag(raw_uid="tag-1", categories={TagCategory.free_form}),
            RawTag(raw_uid="tag-2", categories={TagCategory.free_form}),
            RawTag(raw_uid="tag-3", categories={TagCategory.free_form}),
        ]

    @pytest.mark.asyncio
    async def test_process__temporary_error_processing(
        self, llm_processor: Processor, cataloged_entry: Entry, fake_llm_api_key: LLMApiKey
    ) -> None:

        entry = cataloged_entry.replace(title="@tag-1 @tag-2", body="raise TemporaryError")

        llm_processor.general_api_key = LLMGeneralApiKey(fake_llm_api_key)

        with pytest.raises(errors.TemporaryErrorInProcessor):
            await llm_processor.process(entry)
