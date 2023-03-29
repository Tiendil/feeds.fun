
import uuid

import pydantic


class Feed(pydantic.BaseModel):
    id: uuid.UUID|None = None
    url: str
