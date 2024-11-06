import datetime
import decimal
import enum
from typing import Annotated, NewType

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.feeds.entities import FeedId

LLMApiKey = NewType("LLMApiKey", str)
LLMUserApiKey = NewType("LLMUserApiKey", LLMApiKey)
LLMCollectionApiKey = NewType("LLMCollectionApiKey", LLMApiKey)
LLMGeneralApiKey = NewType("LLMGeneralApiKey", LLMApiKey)

USDCost = NewType("USDCost", decimal.Decimal)

LLMTokens = NewType("LLMTokens", int)


class LLMProvider(enum.StrEnum):
    test = "test"
    openai = "openai"
    google = "google"


class ModelInfo(pydantic.BaseModel):
    provider: LLMProvider
    name: str
    max_context_size: LLMTokens
    max_return_tokens: LLMTokens

    # protection from overuse/overspend
    max_tokens_per_entry: LLMTokens

    input_1m_tokens_cost: USDCost
    output_1m_tokens_cost: USDCost

    # TODO: test
    def tokens_cost(self, input_tokens: LLMTokens, output_tokens: LLMTokens) -> USDCost:
        cost = (
            self.input_1m_tokens_cost * input_tokens / 1_000_000
            + self.output_1m_tokens_cost * output_tokens / 1_000_000
        )
        return USDCost(cost)


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
    system: Annotated[str, pydantic.StringConstraints(strip_whitespace=True)]
    max_return_tokens: LLMTokens
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

    def input_tokens(self) -> int:
        raise NotImplementedError("Must be implemented in subclasses")

    def output_tokens(self) -> int:
        raise NotImplementedError("Must be implemented in subclasses")


class APIKeyUsage(BaseEntity):
    model_config = pydantic.ConfigDict(frozen=False)

    provider: LLMProvider
    user_id: UserId | None
    api_key: LLMApiKey
    reserved_cost: USDCost
    input_tokens: LLMTokens | None
    output_tokens: LLMTokens | None
    used_cost: USDCost | None
    interval_started_at: datetime.datetime

    def cost_to_register(self) -> USDCost:
        if self.used_cost:
            return self.used_cost

        return self.reserved_cost


class UserKeyInfo(BaseEntity):
    user_id: UserId
    api_key: LLMApiKey | None
    max_tokens_cost_in_month: USDCost
    process_entries_not_older_than: datetime.timedelta
    cost_used: USDCost


class SelectKeyContext(BaseEntity):
    llm_config: LLMConfiguration
    feed_ids: set[FeedId]
    entry_age: datetime.timedelta
    reserved_cost: USDCost
    interval_started_at: datetime.datetime = pydantic.Field(default_factory=month_interval_start)
    collections_api_key: LLMCollectionApiKey | None
    general_api_key: LLMGeneralApiKey | None
