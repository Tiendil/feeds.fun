import datetime

from ffun.core.entities import BaseEntity
from ffun.domain.entities import RuleId, UserId


class Rule(BaseEntity):
    id: RuleId
    user_id: UserId

    required_tags: set[int]
    excluded_tags: set[int]
    score: int

    created_at: datetime.datetime
    updated_at: datetime.datetime
