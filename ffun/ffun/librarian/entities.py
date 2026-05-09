import enum
from typing import TYPE_CHECKING, Annotated, Literal, Protocol

import pydantic
from pydantic_core import PydanticCustomError

from ffun.core import logging
from ffun.core.entities import BaseEntity
from ffun.dispatcher.entities import ProcessorDispatchRoute
from ffun.domain.entities import LLMTokens, ProcessorId
from ffun.llms_framework.entities import (
    LLMApiKeyType,
    LLMCollectionApiKey,
    LLMConfiguration,
    LLMGeneralApiKey,
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


class BaseProcessor(BaseEntity):
    id: ProcessorId
    enabled: bool
    workers: int
    name: str
    type: ProcessorType
    allowed_for_collections: bool
    allowed_for_users: bool

    def dispatch_routes(self) -> tuple[ProcessorDispatchRoute, ...]:
        return (
            ProcessorDispatchRoute(
                allowed_for_collections=self.allowed_for_collections,
                allowed_for_users=self.allowed_for_users,
            ),
        )


class DomainProcessor(BaseProcessor):
    type: Literal[ProcessorType.domain] = ProcessorType.domain


class NativeTagsProcessor(BaseProcessor):
    type: Literal[ProcessorType.native_tags] = ProcessorType.native_tags


class UpperCaseTitleProcessor(BaseProcessor):
    type: Literal[ProcessorType.upper_case_title] = ProcessorType.upper_case_title


_general_key_warning = "I understand that setting this key may be DANGEROUS and COSTLY."


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

    collections_api_key: LLMCollectionApiKey | None = None
    general_api_key: LLMGeneralApiKey | None = None

    general_api_key_warning: str | None = None

    def collection_api_key_dispatch_route(self) -> ProcessorDispatchRoute | None:
        if self.collections_api_key is None or not self.allowed_for_collections:
            return None

        return ProcessorDispatchRoute(
            allowed_for_collections=True,
            allowed_for_users=False,
            llm_api_key_type=LLMApiKeyType.collection,
        )

    def general_api_key_dispatch_route(self) -> ProcessorDispatchRoute | None:
        if self.general_api_key is None:
            return None

        if not (self.allowed_for_collections or self.allowed_for_users):
            return None

        return ProcessorDispatchRoute(
            allowed_for_collections=self.allowed_for_collections,
            allowed_for_users=self.allowed_for_users,
            llm_api_key_type=LLMApiKeyType.general,
        )

    def user_api_key_dispatch_route(self) -> ProcessorDispatchRoute | None:
        if not self.allowed_for_users:
            return None

        return ProcessorDispatchRoute(
            allowed_for_collections=False,
            allowed_for_users=True,
            llm_api_key_type=LLMApiKeyType.user,
        )

    def dispatch_routes(self) -> tuple[ProcessorDispatchRoute, ...]:
        routes = (
            self.collection_api_key_dispatch_route(),
            self.general_api_key_dispatch_route(),
            self.user_api_key_dispatch_route(),
        )

        return tuple(route for route in routes if route is not None)

    @pydantic.model_validator(mode="before")
    @classmethod
    def collections_api_key_none(cls, data: dict[str, object]) -> object:
        """Translate empty string to None because TOML does not support None value"""
        if data.get("collections_api_key") == "":
            data["collections_api_key"] = None

        return data

    @pydantic.model_validator(mode="after")
    def require_collections_or_general_key_if_collections_are_allowed(self) -> "LLMGeneralProcessor":
        if self.allowed_for_collections and self.collections_api_key is None and self.general_api_key is None:
            raise PydanticCustomError(
                "collections_or_general_key_required_for_collections",
                "Collections API key or General API key must be set "
                "if you want to use this processor to process feeds from collections. "
                "Feeds Fun must guarantee that users will not pay for processing feeds from collections.",
            )

        return self

    @pydantic.model_validator(mode="before")
    @classmethod
    def general_api_key_none(cls, data: dict[str, object]) -> object:
        """Translate empty string to None because TOML does not support None value"""
        if data.get("general_api_key") == "":
            data["general_api_key"] = None

        return data

    @pydantic.model_validator(mode="after")
    def general_api_key_warning_check(self) -> "LLMGeneralProcessor":
        if self.general_api_key is not None and self.general_api_key_warning != _general_key_warning:
            raise PydanticCustomError(
                "you_must_confirm_general_api_key_usage",
                "You must confirm that you understand the risks of using the General API key. "
                f"Set `general_api_key_warning` to the value '{_general_key_warning}'.",
            )

        return self


TagProcessor = Annotated[
    DomainProcessor | NativeTagsProcessor | UpperCaseTitleProcessor | LLMGeneralProcessor,
    pydantic.Field(discriminator="type"),
]


class ProcessorsConfig(pydantic.BaseModel):
    tag_processors: tuple[TagProcessor, ...]
