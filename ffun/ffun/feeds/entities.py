
import datetime
import uuid

import pydantic


class Feed(pydantic.BaseModel):
    id: uuid.UUID
    url: str
    load_attempted_at: datetime.datetime|None = None
    loaded_at: datetime.datetime|None = None
