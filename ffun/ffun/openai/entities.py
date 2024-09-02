import datetime
import enum
import uuid
from typing import Protocol

import pydantic

from ffun.domain.datetime_intervals import month_interval_start
from ffun.feeds.entities import FeedId


class APIKeyUsage(pydantic.BaseModel):
    user_id: uuid.UUID
    api_key: str
    reserved_tokens: int
    used_tokens: int | None
    interval_started_at: datetime.datetime

    def spent_tokens(self) -> int:
        if self.used_tokens:
            return self.used_tokens

        return self.reserved_tokens


class UserKeyInfo(pydantic.BaseModel):
    user_id: uuid.UUID
    api_key: str | None
    max_tokens_in_month: int
    process_entries_not_older_than: datetime.timedelta
    tokens_used: int


class SelectKeyContext(pydantic.BaseModel):
    feed_id: FeedId
    entry_age: datetime.timedelta
    reserved_tokens: int
    interval_started_at: datetime.datetime = pydantic.Field(default_factory=month_interval_start)


class KeySelector(Protocol):
    async def __call__(self, context: SelectKeyContext) -> APIKeyUsage | None:
        """Selector function"""
