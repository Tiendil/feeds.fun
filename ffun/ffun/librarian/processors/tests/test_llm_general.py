import pytest

from ffun.dispatcher.entities import ProcessorRouteId
from ffun.domain.entities import FeedId
from ffun.feeds_links import domain as fl_domain
from ffun.librarian import errors
from ffun.librarian.entities import LLMGeneralProcessorRoute
from ffun.librarian.processors.base import ProcessorContext
from ffun.librarian.processors.llm_general import Processor
from ffun.librarian.tag_extractors import dog_tags_extractor
from ffun.librarian.text_cleaners import clear_nothing
from ffun.library.entities import Entry
from ffun.llms_framework.entities import (
    ChatRequest,
    LLMApiKey,
    LLMConfiguration,
    LLMProvider,
    LLMTokens,
    UserKeyInfo,
)
from ffun.llms_framework.provider_interface import ChatResponseTest
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagCategory

CONFIGURED_KEY_ROUTE_ID = ProcessorRouteId("configured-key-route")
USER_KEY_ROUTE_ID = ProcessorRouteId("user-key-route")
UNKNOWN_ROUTE_ID = ProcessorRouteId("unknown-route")


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
    def llm_processor(self, llm_config: LLMConfiguration, fake_llm_api_key: LLMApiKey) -> Processor:
        return Processor(
            name="test-llm-processor",
            llm_provider=LLMProvider.test,
            llm_config=llm_config,
            entry_template="{entry.title} {entry.body}",
            text_cleaner=clear_nothing,
            tag_extractor=dog_tags_extractor,
            max_tokens_per_entry=LLMTokens(1_000),
            text_parts_intersection=100,
            routes=(
                LLMGeneralProcessorRoute(
                    id=USER_KEY_ROUTE_ID,
                    allowed_for_collections=False,
                    allowed_for_users=True,
                    api_key=None,
                ),
                LLMGeneralProcessorRoute(
                    id=CONFIGURED_KEY_ROUTE_ID,
                    allowed_for_collections=True,
                    allowed_for_users=False,
                    api_key=fake_llm_api_key,
                ),
            ),
        )

    def test_extract_tags__deduplicates_extracted_tags(self, llm_processor: Processor) -> None:

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

    def _requests(self, llm_processor: Processor, text: str) -> list[ChatRequest]:
        return list(
            llm_processor.llm_provider.prepare_requests(
                llm_processor.llm_config,
                text,
                llm_processor.text_parts_intersection,
            )
        )

    @pytest.mark.asyncio
    async def test__api_key_usage__configured_key_found(
        self, llm_processor: Processor, cataloged_entry: Entry, fake_llm_api_key: LLMApiKey
    ) -> None:
        api_key_usage = await llm_processor._api_key_usage(
            entry=cataloged_entry,
            requests=self._requests(llm_processor, "some text"),
            context=ProcessorContext(route_id=CONFIGURED_KEY_ROUTE_ID),
        )

        assert api_key_usage is not None
        assert api_key_usage.api_key == fake_llm_api_key
        assert api_key_usage.user_id is None

    @pytest.mark.asyncio
    async def test__api_key_usage__unknown_route(self, llm_processor: Processor, cataloged_entry: Entry) -> None:
        with pytest.raises(errors.UnknownProcessorRoute):
            await llm_processor._api_key_usage(
                entry=cataloged_entry,
                requests=self._requests(llm_processor, "some text"),
                context=ProcessorContext(route_id=UNKNOWN_ROUTE_ID),
            )

    @pytest.mark.asyncio
    async def test__api_key_usage__user_key_found(
        self,
        llm_processor: Processor,
        cataloged_entry: Entry,
        loaded_feed_id: FeedId,
        user_key_info: UserKeyInfo,
    ) -> None:
        assert user_key_info.api_key is not None

        await fl_domain.add_link(user_key_info.user_id, loaded_feed_id)

        api_key_usage = await llm_processor._api_key_usage(
            entry=cataloged_entry,
            requests=self._requests(llm_processor, "some text"),
            context=ProcessorContext(route_id=USER_KEY_ROUTE_ID),
        )

        assert api_key_usage is not None
        assert api_key_usage.api_key == user_key_info.api_key
        assert api_key_usage.user_id == user_key_info.user_id

    @pytest.mark.asyncio
    async def test__api_key_usage__user_key_not_found(self, llm_processor: Processor, cataloged_entry: Entry) -> None:
        assert (
            await llm_processor._api_key_usage(
                entry=cataloged_entry,
                requests=self._requests(llm_processor, "some text"),
                context=ProcessorContext(route_id=USER_KEY_ROUTE_ID),
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_process__no_api_key_found(self, llm_processor: Processor, cataloged_entry: Entry) -> None:
        with pytest.raises(errors.SkipEntryProcessing):
            await llm_processor.process(cataloged_entry, context=ProcessorContext(route_id=USER_KEY_ROUTE_ID))

    @pytest.mark.asyncio
    async def test_process__has_api_key_found(self, llm_processor: Processor, cataloged_entry: Entry) -> None:

        entry = cataloged_entry.replace(title="@tag-1 @tag-2", body="@tag-3 @tag-2")

        tags = await llm_processor.process(entry, context=ProcessorContext(route_id=CONFIGURED_KEY_ROUTE_ID))

        tags.sort(key=lambda x: x.raw_uid)

        assert tags == [
            RawTag(raw_uid="tag-1", categories={TagCategory.free_form}),
            RawTag(raw_uid="tag-2", categories={TagCategory.free_form}),
            RawTag(raw_uid="tag-3", categories={TagCategory.free_form}),
        ]

    @pytest.mark.asyncio
    async def test_process__temporary_error_processing(self, llm_processor: Processor, cataloged_entry: Entry) -> None:

        entry = cataloged_entry.replace(title="@tag-1 @tag-2", body="raise TemporaryError")

        with pytest.raises(errors.TemporaryErrorInProcessor):
            await llm_processor.process(entry, context=ProcessorContext(route_id=CONFIGURED_KEY_ROUTE_ID))
