import datetime
import enum
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

import pydantic
from pydantic_core import PydanticCustomError

from ffun.core import logging
from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId
from ffun.llms_framework.entities import LLMCollectionApiKey, LLMConfiguration, LLMGeneralApiKey, LLMProvider

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


class ProcessorPointer(BaseEntity):
    processor_id: int
    pointer_created_at: datetime.datetime
    pointer_entry_id: EntryId


class BaseProcessor(BaseEntity):
    id: int
    enabled: bool
    workers: int
    name: str
    type: ProcessorType
    allowed_for_collections: bool
    allowed_for_users: bool


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

    llm_provider: LLMProvider

    llm_config: LLMConfiguration

    collections_api_key: LLMCollectionApiKey | None = None
    general_api_key: LLMGeneralApiKey | None = None

    general_api_key_warning: str | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def collections_api_key_none(cls, data: Any) -> Any:
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
    def general_api_key_none(cls, data: Any) -> Any:
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
