import datetime
import enum
import uuid
from typing import Annotated, Any, Literal

import pydantic

from ffun.core import logging
from ffun.core.entities import BaseEntity
from ffun.llms_framework.entities import LLMConfiguration, Provider, LLMCollectionApiKey, LLMGeneralApiKey

logger = logging.get_module_logger()


class ProcessorType(enum.StrEnum):
    domain = "domain"
    native_tags = "native_tags"
    upper_case_title = "upper_case_title"
    llm_general = "llm_general"


class ProcessorPointer(BaseEntity):
    processor_id: int
    pointer_created_at: datetime.datetime
    pointer_entry_id: uuid.UUID


class BaseProcessor(BaseEntity):
    id: int
    enabled: bool
    workers: int
    name: str
    type: ProcessorType


class DomainProcessor(BaseProcessor):
    type: Literal[ProcessorType.domain] = ProcessorType.domain


class NativeTagsProcessor(BaseProcessor):
    type: Literal[ProcessorType.native_tags] = ProcessorType.native_tags


class UpperCaseTitleProcessor(BaseProcessor):
    type: Literal[ProcessorType.upper_case_title] = ProcessorType.upper_case_title


class LLMGeneralProcessor(BaseProcessor):
    type: Literal[ProcessorType.llm_general] = ProcessorType.llm_general

    # TODO: validate that template will render correctly
    entry_template: str

    # TODO: validate that text cleaner is importable and works
    text_cleaner: str

    # TODO: validate that text extractor is importable and works
    tags_extractor: str

    llm_provider: Provider

    llm_config: LLMConfiguration

    collections_api_key: LLMCollectionApiKey | None = None
    general_api_key: LLMGeneralApiKey | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def collections_api_key_none(cls, data: Any) -> Any:
        """Translate empty string to None because TOML does not support None value"""
        if data.get("collections_api_key") == "":
            data["collections_api_key"] = None

        return data

    # TODO: remove this after separating collections from other feeds
    @pydantic.model_validator(mode="after")
    def collections_api_key_warning(self) -> "LLMGeneralProcessor":
        if self.collections_api_key is None:
            logger.warning("collections_api_key_is_not_set", comment="Collection feeds will be treated as general")

        return self

    @pydantic.model_validator(mode="before")
    @classmethod
    def general_api_key_none(cls, data: Any) -> Any:
        """Translate empty string to None because TOML does not support None value"""
        if data.get("general_api_key") == "":
            data["general_api_key"] = None

        return data

    # TODO: allow using this key to all entries
    @pydantic.model_validator(mode="after")
    def general_api_key_must_be_none_in_prod(self) -> "LLMGeneralProcessor":
        # TODO: allow in prod, but add double check
        # TODO: this component should not depend on the environment
        #       move environment settings to the domain component
        from ffun.application.settings import settings as app_settings

        if app_settings.environment == "prod" and self.general_api_key is not None:
            raise ValueError("General API key must be None in prod")

        return self


TagProcessor = Annotated[
    DomainProcessor | NativeTagsProcessor | UpperCaseTitleProcessor | LLMGeneralProcessor,
    pydantic.Field(discriminator="type"),
]


class ProcessorsConfig(pydantic.BaseModel):
    tag_processors: tuple[TagProcessor, ...]
