import datetime

import pydantic

from ffun.domain.entities import RuleId, UserId


class BaseRule(pydantic.BaseModel):
    required_tags: set[int]
    excluded_tags: set[int]
    score: int


class Rule(BaseRule):
    id: RuleId
    user_id: UserId
    created_at: datetime.datetime
    updated_at: datetime.datetime
