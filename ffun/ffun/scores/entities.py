import datetime

from ffun.core.entities import BaseEntity
from ffun.domain.entities import RuleId, TagId, UserId


class Rule(BaseEntity):
    id: RuleId
    user_id: UserId

    required_tags: set[TagId]
    excluded_tags: set[TagId]
    score: int

    created_at: datetime.datetime
    updated_at: datetime.datetime
