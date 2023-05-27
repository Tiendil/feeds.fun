import enum
import uuid

import pydantic


class Service(int, enum.Enum):
    supertokens = 1


class User(pydantic.BaseModel):
    id: uuid.UUID
