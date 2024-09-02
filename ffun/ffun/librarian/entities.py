import datetime
import uuid
import pydantic
import enum
from typing import Literal

from ffun.core.entities import BaseEntity
from ffun.llms_framework.entities import LLMConfiguration


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
    llm_config: LLMConfiguration


TagProcessor = DomainProcessor | NativeTagsProcessor | UpperCaseTitleProcessor | LLMGeneralProcessor


class ProcessorsConfig(pydantic.BaseModel):
    processors: list[TagProcessor]
