import datetime
import uuid

import pydantic


class Rule(pydantic.BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tags: set[int]
    score: int
    created_at: datetime.datetime
