import datetime
import enum
import uuid
from typing import NewType

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.datetime_intervals import month_interval_start
from ffun.feeds.entities import FeedId


LLMApiKey = NewType("LLMApiKey", str)
LLMUserApiKey = NewType("LLMUserApiKey", LLMApiKey)
LLMCollectionApiKey = NewType("LLMCollectionApiKey", LLMApiKey)
LLMGeneralApiKey = NewType("LLMGeneralApiKey", LLMApiKey)


class Provider(enum.StrEnum):
    test = "test"
    openai = "openai"
    google = "google"


class ModelInfo(pydantic.BaseModel):
    provider: Provider
    name: str
    max_context_size: int
    max_return_tokens: int

    # protection from overuse/overspend
    max_tokens_per_entry: int


class KeyStatus(str, enum.Enum):
    works = "works"
    broken = "broken"
    quota = "quota"
    unknown = "unknown"


# Generally, different LLM providers can have different config parameters with different names.
# But for simplicity, for now, we will use the unified config for all providers.
# We'll split it later if needed.
class LLMConfiguration(BaseEntity):
    model: str
    system: str  # TODO: trim
    max_return_tokens: int
    text_parts_intersection: int
    temperature: float
    top_p: float
    presence_penalty: float
    frequency_penalty: float


class ChatRequest(BaseEntity):
    pass


class ChatResponse(BaseEntity):

    def response_content(self) -> str:
        raise NotImplementedError("Must be implemented in subclasses")

    def spent_tokens(self) -> int:
        raise NotImplementedError("Must be implemented in subclasses")


class APIKeyUsage(BaseEntity):
    model_config = pydantic.ConfigDict(frozen=False)

    user_id: uuid.UUID | None
    api_key: LLMApiKey
    reserved_tokens: int
    used_tokens: int | None
    interval_started_at: datetime.datetime

    def spent_tokens(self) -> int:
        if self.used_tokens:
            return self.used_tokens

        return self.reserved_tokens


class UserKeyInfo(BaseEntity):
    user_id: uuid.UUID
    api_key: LLMApiKey | None
    max_tokens_in_month: int
    process_entries_not_older_than: datetime.timedelta
    tokens_used: int


class SelectKeyContext(BaseEntity):
    llm_config: LLMConfiguration
    feed_id: FeedId
    entry_age: datetime.timedelta
    reserved_tokens: int
    interval_started_at: datetime.datetime = pydantic.Field(default_factory=month_interval_start)
    collections_api_key: LLMCollectionApiKey | None
    general_api_key: LLMGeneralApiKey | None
