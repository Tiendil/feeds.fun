import enum
from typing import TYPE_CHECKING, Annotated, Literal, Protocol

import pydantic
from pydantic_core import PydanticCustomError

from ffun.core import logging
from ffun.core.entities import BaseEntity
from ffun.dispatcher.entities import ProcessorDispatchRoute, ProcessorRouteId
from ffun.domain.entities import LLMTokens, ProcessorId
from ffun.llms_framework.entities import (
    LLMApiKey,
    LLMConfiguration,
    LLMProvider,
)

logger = logging.get_module_logger()


class TextCleaner(Protocol):
    def __call__(self, text: str) -> str:
        pass


class TagsExtractor(Protocol):
    def __call__(self, text: str) -> set[str]:
        pass


class ProcessorType(enum.StrEnum):
    fake = "fake"
    domain = "domain"
    native_tags = "native_tags"
    upper_case_title = "upper_case_title"
    llm_general = "llm_general"


class ProcessorRoute(BaseEntity):
    id: ProcessorRouteId
    allowed_for_collections: bool = False
    allowed_for_users: bool = False
    allowed_for_quality_tests: bool = False

    def dispatch_route(self) -> ProcessorDispatchRoute:
        return ProcessorDispatchRoute(
            id=self.id,
            allowed_for_collections=self.allowed_for_collections,
            allowed_for_users=self.allowed_for_users,
        )


class BaseProcessor(BaseEntity):
    id: ProcessorId
    enabled: bool
    workers: int
    name: str
    type: ProcessorType
    routes: tuple[ProcessorRoute, ...]

    @pydantic.model_validator(mode="after")
    def only_one_quality_test_route_is_allowed(self) -> "BaseProcessor":
        quality_routes = [route for route in self.routes if route.allowed_for_quality_tests]

        if len(quality_routes) > 1:
            raise PydanticCustomError(
                "too_many_quality_test_routes",
                "Only one route can be allowed for processor quality tests.",
            )

        return self

    @property
    def quality_route_id(self) -> ProcessorRouteId | None:
        for route in self.routes:
            if route.allowed_for_quality_tests:
                return route.id

        return None

    def dispatch_routes(self) -> tuple[ProcessorDispatchRoute, ...]:
        return tuple(route.dispatch_route() for route in self.routes)


class DomainProcessor(BaseProcessor):
    type: Literal[ProcessorType.domain] = ProcessorType.domain


class NativeTagsProcessor(BaseProcessor):
    type: Literal[ProcessorType.native_tags] = ProcessorType.native_tags


class UpperCaseTitleProcessor(BaseProcessor):
    type: Literal[ProcessorType.upper_case_title] = ProcessorType.upper_case_title


class LLMGeneralProcessorRoute(ProcessorRoute):
    api_key: LLMApiKey | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def api_key_none(cls, data: dict[str, object]) -> object:
        """Translate empty string to None because TOML does not support None value"""
        if data.get("api_key") == "":
            data["api_key"] = None

        return data

    @pydantic.model_validator(mode="after")
    def require_api_key_if_collections_are_allowed(self) -> "LLMGeneralProcessorRoute":
        if self.allowed_for_collections and self.api_key is None:
            raise PydanticCustomError(
                "api_key_required_for_collections",
                "API key must be set on routes that process feeds from collections. "
                "Feeds Fun must guarantee that users will not pay for processing feeds from collections.",
            )

        return self


if TYPE_CHECKING:
    # TODO: fix after Pydantic learn how to process such parametrization at runtime
    PydanticTextCleaner = pydantic.ImportString[TextCleaner]
    PydanticTagsExtractor = pydantic.ImportString[TagsExtractor]
else:
    PydanticTextCleaner = pydantic.ImportString
    PydanticTagsExtractor = pydantic.ImportString


class LLMGeneralProcessor(BaseProcessor):

    # arbitrary_types_allowed is required for parametrization of pydantic.ImportString
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    type: Literal[ProcessorType.llm_general] = ProcessorType.llm_general

    # TODO: validate that template will render correctly
    entry_template: str

    text_cleaner: PydanticTextCleaner
    tags_extractor: PydanticTagsExtractor

    # `max_tokens_per_entry` does not include output tokens,
    # because it complicates understanding and configuring this parameter for users
    # as well as testing changes
    # So, `max_tokens_per_entry` tells how we cut the original text,
    # regardless of the system prompt or output limit
    max_tokens_per_entry: LLMTokens
    text_parts_intersection: int

    llm_provider: LLMProvider

    llm_config: LLMConfiguration

    routes: tuple[LLMGeneralProcessorRoute, ...]


TagProcessor = Annotated[
    DomainProcessor | NativeTagsProcessor | UpperCaseTitleProcessor | LLMGeneralProcessor,
    pydantic.Field(discriminator="type"),
]


class ProcessorsConfig(pydantic.BaseModel):
    tag_processors: tuple[TagProcessor, ...]
