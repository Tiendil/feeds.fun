import pydantic
import pytest

from ffun.dispatcher.entities import ProcessorDispatchRoute, ProcessorRouteId
from ffun.domain.entities import ProcessorId
from ffun.librarian.entities import (
    DomainProcessor,
    LLMGeneralProcessor,
    LLMGeneralProcessorRoute,
    ProcessorRoute,
)
from ffun.librarian.tag_extractors import dog_tags_extractor
from ffun.librarian.text_cleaners import clear_nothing
from ffun.llms_framework.entities import (
    LLMApiKey,
    LLMConfiguration,
    LLMProvider,
    LLMTokens,
)


class TestBaseProcessor:
    def test_route_defaults(self) -> None:
        route = ProcessorRoute(id=ProcessorRouteId("default"))

        assert not route.allowed_for_collections
        assert not route.allowed_for_users
        assert not route.allowed_for_quality_tests

    def test_dispatch_routes(self) -> None:
        processor = DomainProcessor(
            id=ProcessorId(101),
            enabled=True,
            workers=1,
            name="test-processor",
            routes=(
                ProcessorRoute(
                    id=ProcessorRouteId("domain-route"),
                    allowed_for_collections=True,
                    allowed_for_users=False,
                    allowed_for_quality_tests=True,
                ),
            ),
        )

        assert processor.dispatch_routes() == (
            ProcessorDispatchRoute(
                id=ProcessorRouteId("domain-route"),
                allowed_for_collections=True,
                allowed_for_users=False,
            ),
        )

    def test_quality_route_id__returns_configured_quality_route(self) -> None:
        processor = DomainProcessor(
            id=ProcessorId(101),
            enabled=True,
            workers=1,
            name="test-processor",
            routes=(
                ProcessorRoute(id=ProcessorRouteId("default")),
                ProcessorRoute(
                    id=ProcessorRouteId("quality-route"),
                    allowed_for_quality_tests=True,
                ),
            ),
        )

        assert processor.quality_route_id == ProcessorRouteId("quality-route")

    def test_quality_route_id__returns_none_without_quality_route(self) -> None:
        processor = DomainProcessor(
            id=ProcessorId(101),
            enabled=True,
            workers=1,
            name="test-processor",
            routes=(ProcessorRoute(id=ProcessorRouteId("default")),),
        )

        assert processor.quality_route_id is None

    def test_quality_route_id__multiple_quality_routes_are_forbidden(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            DomainProcessor(
                id=ProcessorId(101),
                enabled=True,
                workers=1,
                name="test-processor",
                routes=(
                    ProcessorRoute(
                        id=ProcessorRouteId("first-quality-route"),
                        allowed_for_quality_tests=True,
                    ),
                    ProcessorRoute(
                        id=ProcessorRouteId("second-quality-route"),
                        allowed_for_quality_tests=True,
                    ),
                ),
            )

        assert exc_info.value.errors()[0]["type"] == "too_many_quality_test_routes"  # type: ignore


class TestLLMGeneralProcessorRoute:
    def test_api_key_is_required_if_collections_enabled(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LLMGeneralProcessorRoute(
                id=ProcessorRouteId("collection-route"),
                allowed_for_collections=True,
                allowed_for_users=False,
                api_key=None,
            )

        assert exc_info.value.errors()[0]["type"] == "api_key_required_for_collections"  # type: ignore

    def test_api_key__empty_string_is_normalized_to_none(self) -> None:
        route = LLMGeneralProcessorRoute(
            id=ProcessorRouteId("user-route"),
            allowed_for_collections=False,
            allowed_for_users=True,
            api_key=LLMApiKey(""),
        )

        assert route.api_key is None


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
        routes: tuple[LLMGeneralProcessorRoute, ...],
    ) -> LLMGeneralProcessor:
        return LLMGeneralProcessor(
            id=ProcessorId(666),
            enabled=True,
            workers=1,
            name="test-processor",
            routes=routes,
            llm_provider=LLMProvider.test,
            llm_config=llm_config,
            entry_template="<h1>{entry.title}</h1><a href='{entry.external_url}'>full article</a>{entry.body}",
            text_cleaner=clear_nothing,
            tags_extractor=dog_tags_extractor,
            max_tokens_per_entry=LLMTokens(5_000),
            text_parts_intersection=113,
        )

    def test_dispatch_routes__preserves_configured_order_and_hides_route_params(
        self, llm_config: LLMConfiguration
    ) -> None:
        processor = self.processor_config(
            llm_config,
            routes=(
                LLMGeneralProcessorRoute(
                    id=ProcessorRouteId("collection-route"),
                    allowed_for_collections=True,
                    allowed_for_users=False,
                    api_key=LLMApiKey("collection-key"),
                ),
                LLMGeneralProcessorRoute(
                    id=ProcessorRouteId("configured-user-route"),
                    allowed_for_collections=True,
                    allowed_for_users=True,
                    allowed_for_quality_tests=True,
                    api_key=LLMApiKey("general-key"),
                ),
                LLMGeneralProcessorRoute(
                    id=ProcessorRouteId("user-route"),
                    allowed_for_collections=False,
                    allowed_for_users=True,
                    api_key=None,
                ),
            ),
        )

        assert processor.dispatch_routes() == (
            ProcessorDispatchRoute(
                id=ProcessorRouteId("collection-route"),
                allowed_for_collections=True,
                allowed_for_users=False,
            ),
            ProcessorDispatchRoute(
                id=ProcessorRouteId("configured-user-route"),
                allowed_for_collections=True,
                allowed_for_users=True,
            ),
            ProcessorDispatchRoute(
                id=ProcessorRouteId("user-route"),
                allowed_for_collections=False,
                allowed_for_users=True,
            ),
        )
        assert processor.quality_route_id == ProcessorRouteId("configured-user-route")
