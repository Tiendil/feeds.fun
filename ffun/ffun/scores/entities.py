import datetime
import uuid

import pydantic


class BaseRule(pydantic.BaseModel):
    tags: set[int]
    score: int


class Rule(BaseRule):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
