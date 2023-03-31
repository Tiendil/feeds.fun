
import datetime
import uuid

import pydantic


class Feed(pydantic.BaseModel):
    id: uuid.UUID
    url: str
    loaded_at: datetime.datetime = datetime.datetime.min
