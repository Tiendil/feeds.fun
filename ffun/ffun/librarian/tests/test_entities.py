import pydantic
import pytest

from ffun.dispatcher.entities import ProcessorDispatchRoute
from ffun.librarian.entities import DomainProcessor, LLMGeneralProcessor
from ffun.librarian.tag_extractors import dog_tags_extractor
from ffun.librarian.text_cleaners import clear_nothing
from ffun.llms_framework.entities import (
    LLMApiKey,
    LLMApiKeyType,
    LLMCollectionApiKey,
    LLMConfiguration,
    LLMGeneralApiKey,
    LLMProvider,
    LLMTokens,
)

_general_key_warning = "I understand that setting this key may be DANGEROUS and COSTLY."


class TestBaseProcessor:
    def test_dispatch_routes(self) -> None:
        processor = DomainProcessor(
            id=101,
            enabled=True,
            workers=1,
            name="test-processor",
            allowed_for_collections=True,
            allowed_for_users=False,
        )

        assert processor.dispatch_routes() == (
            ProcessorDispatchRoute(
                allowed_for_collections=True,
                allowed_for_users=False,
            ),
        )


class TestLLMGeneralProcessor:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model",
            system="some system prompt",
            max_return_tokens=LLMTokens(1017),
            temperature=0.3,
            top_p=0.9,
        )

    def processor_config(
        self,
        llm_config: LLMConfiguration,
        *,
        allowed_for_collections: bool,
        allowed_for_users: bool,
        collections_api_key: LLMCollectionApiKey | None = None,
        general_api_key: LLMGeneralApiKey | None = None,
    ) -> LLMGeneralProcessor:
        return LLMGeneralProcessor(
            id=666,
            enabled=True,
            workers=1,
            name="test-processor",
            allowed_for_collections=allowed_for_collections,
            allowed_for_users=allowed_for_users,
            llm_provider=LLMProvider.test,
            llm_config=llm_config,
            entry_template="<h1>{entry.title}</h1><a href='{entry.external_url}'>full article</a>{entry.body}",
            text_cleaner=clear_nothing,
            tags_extractor=dog_tags_extractor,
            max_tokens_per_entry=LLMTokens(5_000),
            text_parts_intersection=113,
            collections_api_key=collections_api_key,
            general_api_key=general_api_key,
            general_api_key_warning=_general_key_warning if general_api_key is not None else None,
        )

    def test_api_key_is_required_if_collections_enbabled(self, llm_config: LLMConfiguration) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LLMGeneralProcessor(
                id=666,
                enabled=True,
                workers=1,
                name="test-processor",
                allowed_for_collections=True,
                allowed_for_users=False,
                llm_provider=LLMProvider.test,
                llm_config=llm_config,
                entry_template="<h1>{entry.title}</h1><a href='{entry.external_url}'>full article</a>{entry.body}",
                text_cleaner=clear_nothing,
                tags_extractor=dog_tags_extractor,
                max_tokens_per_entry=LLMTokens(5_000),
                text_parts_intersection=113,
                collections_api_key=None,
                general_api_key=None,
            )

        assert (
            exc_info.value.errors()[0]["type"] == "collections_or_general_key_required_for_collections"  # type: ignore
        )

    @pytest.mark.parametrize(
        "allowed_for_collections, collections_api_key, expected_route",
        [
            (
                True,
                LLMCollectionApiKey(LLMApiKey("collection-key")),
                ProcessorDispatchRoute(
                    allowed_for_collections=True,
                    allowed_for_users=False,
                    llm_api_key_type=LLMApiKeyType.collection,
                ),
            ),
            (True, None, None),
            (False, LLMCollectionApiKey(LLMApiKey("collection-key")), None),
            (False, None, None),
        ],
    )
    def test_collection_api_key_dispatch_route(
        self,
        llm_config: LLMConfiguration,
        allowed_for_collections: bool,
        collections_api_key: LLMCollectionApiKey | None,
        expected_route: ProcessorDispatchRoute | None,
    ) -> None:
        processor = self.processor_config(
            llm_config,
            allowed_for_collections=allowed_for_collections,
            allowed_for_users=False,
            collections_api_key=collections_api_key,
            general_api_key=LLMGeneralApiKey(LLMApiKey("general-key")) if allowed_for_collections else None,
        )

        assert processor.collection_api_key_dispatch_route() == expected_route

    @pytest.mark.parametrize(
        "allowed_for_collections, allowed_for_users, general_api_key, expected_route",
        [
            (False, False, None, None),
            (
                False,
                False,
                LLMGeneralApiKey(LLMApiKey("general-key")),
                None,
            ),
            (False, True, None, None),
            (
                False,
                True,
                LLMGeneralApiKey(LLMApiKey("general-key")),
                ProcessorDispatchRoute(
                    allowed_for_collections=False,
                    allowed_for_users=True,
                    llm_api_key_type=LLMApiKeyType.general,
                ),
            ),
            (True, False, None, None),
            (
                True,
                False,
                LLMGeneralApiKey(LLMApiKey("general-key")),
                ProcessorDispatchRoute(
                    allowed_for_collections=True,
                    allowed_for_users=False,
                    llm_api_key_type=LLMApiKeyType.general,
                ),
            ),
            (True, True, None, None),
            (
                True,
                True,
                LLMGeneralApiKey(LLMApiKey("general-key")),
                ProcessorDispatchRoute(
                    allowed_for_collections=True,
                    allowed_for_users=True,
                    llm_api_key_type=LLMApiKeyType.general,
                ),
            ),
        ],
    )
    def test_general_api_key_dispatch_route(
        self,
        llm_config: LLMConfiguration,
        allowed_for_collections: bool,
        allowed_for_users: bool,
        general_api_key: LLMGeneralApiKey | None,
        expected_route: ProcessorDispatchRoute | None,
    ) -> None:
        processor = self.processor_config(
            llm_config,
            allowed_for_collections=allowed_for_collections,
            allowed_for_users=allowed_for_users,
            collections_api_key=LLMCollectionApiKey(LLMApiKey("collection-key")) if allowed_for_collections else None,
            general_api_key=general_api_key,
        )

        assert processor.general_api_key_dispatch_route() == expected_route

    @pytest.mark.parametrize(
        "allowed_for_collections, allowed_for_users, expected_route",
        [
            (False, False, None),
            (
                False,
                True,
                ProcessorDispatchRoute(
                    allowed_for_collections=False,
                    allowed_for_users=True,
                    llm_api_key_type=LLMApiKeyType.user,
                ),
            ),
            (True, False, None),
            (
                True,
                True,
                ProcessorDispatchRoute(
                    allowed_for_collections=False,
                    allowed_for_users=True,
                    llm_api_key_type=LLMApiKeyType.user,
                ),
            ),
        ],
    )
    def test_user_api_key_dispatch_route(
        self,
        llm_config: LLMConfiguration,
        allowed_for_collections: bool,
        allowed_for_users: bool,
        expected_route: ProcessorDispatchRoute | None,
    ) -> None:
        processor = self.processor_config(
            llm_config,
            allowed_for_collections=allowed_for_collections,
            allowed_for_users=allowed_for_users,
            general_api_key=LLMGeneralApiKey(LLMApiKey("general-key")) if allowed_for_collections else None,
        )

        assert processor.user_api_key_dispatch_route() == expected_route

    def test_dispatch_routes__filters_nones_and_preserves_order(self, llm_config: LLMConfiguration) -> None:
        processor = self.processor_config(
            llm_config,
            allowed_for_collections=True,
            allowed_for_users=True,
            collections_api_key=LLMCollectionApiKey(LLMApiKey("collection-key")),
            general_api_key=LLMGeneralApiKey(LLMApiKey("general-key")),
        )

        assert processor.dispatch_routes() == (
            ProcessorDispatchRoute(
                allowed_for_collections=True,
                allowed_for_users=False,
                llm_api_key_type=LLMApiKeyType.collection,
            ),
            ProcessorDispatchRoute(
                allowed_for_collections=True,
                allowed_for_users=True,
                llm_api_key_type=LLMApiKeyType.general,
            ),
            ProcessorDispatchRoute(
                allowed_for_collections=False,
                allowed_for_users=True,
                llm_api_key_type=LLMApiKeyType.user,
            ),
        )

    @pytest.mark.parametrize("key_warning", [None, "wrong warning"])
    def test_general_api_key_warning_check__failed(
        self, llm_config: LLMConfiguration, key_warning: str | None
    ) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LLMGeneralProcessor(
                id=666,
                enabled=True,
                workers=1,
                name="test-processor",
                allowed_for_collections=False,
                allowed_for_users=False,
                llm_provider=LLMProvider.test,
                llm_config=llm_config,
                entry_template="<h1>{entry.title}</h1><a href='{entry.external_url}'>full article</a>{entry.body}",
                text_cleaner=clear_nothing,
                tags_extractor=dog_tags_extractor,
                max_tokens_per_entry=LLMTokens(5_000),
                text_parts_intersection=113,
                collections_api_key=None,
                general_api_key=LLMGeneralApiKey(LLMApiKey("some key")),
                general_api_key_warning=key_warning,
            )

        assert exc_info.value.errors()[0]["type"] == "you_must_confirm_general_api_key_usage"  # type: ignore
