import enum

import pydantic

from ffun.domain.entities import UserId


class Service(int, enum.Enum):
    supertokens = 1
    single = 2


class User(pydantic.BaseModel):
    id: UserId
