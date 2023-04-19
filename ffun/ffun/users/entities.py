import uuid

import pydantic


class User(pydantic.BaseModel):
    id: uuid.UUID
