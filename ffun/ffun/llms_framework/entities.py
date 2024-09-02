import datetime
import enum
import uuid
import decimal
from typing import Protocol
from ffun.core.entities import BaseEntity

from ffun.domain.datetime_intervals import month_interval_start
from ffun.feeds.entities import FeedId

import pydantic


class Provider(enum.StrEnum):
    openai = "openai"
    google = "google"


class ModelInfo(pydantic.BaseModel):
    provider: Provider
    name: str
    max_context_size: int
    max_return_tokens: int


class KeyStatus(str, enum.Enum):
    works = "works"
    broken = "broken"
    quota = "quota"
    unknown = "unknown"


# Generally, different LLM providers can have config parameters with different names.
# But for simplicity, for now, we will use the unified config for all providers.
# We'll split it later if needed.
class LLMConfiguration(BaseEntity):
    model: str
    system: str  # TODO: trim
    max_return_tokens: int
    text_parts_intersection: int
    additional_tokens_per_message: int
    temperature: decimal.Decimal
    top_p: decimal.Decimal
    presence_penalty: decimal.Decimal
    frequency_penalty: decimal.Decimal


class ChatRequest(BaseEntity):
    pass


class ChatResponse(BaseEntity):
    pass


class APIKeyUsage(BaseEntity):
    user_id: uuid.UUID
    api_key: str
    reserved_tokens: int
    used_tokens: int | None
    interval_started_at: datetime.datetime

    def spent_tokens(self) -> int:
        if self.used_tokens:
            return self.used_tokens

        return self.reserved_tokens


class UserKeyInfo(BaseEntity):
    user_id: uuid.UUID
    api_key: str | None
    max_tokens_in_month: int
    process_entries_not_older_than: datetime.timedelta
    tokens_used: int


class SelectKeyContext(BaseEntity):
    feed_id: FeedId
    entry_age: datetime.timedelta
    reserved_tokens: int
    interval_started_at: datetime.datetime = pydantic.Field(default_factory=month_interval_start)


class KeySelector(Protocol):
    async def __call__(self, context: SelectKeyContext) -> APIKeyUsage | None:
        """Selector function"""
