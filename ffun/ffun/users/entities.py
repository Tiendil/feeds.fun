import pydantic

from ffun.domain.entities import UserId


class User(pydantic.BaseModel):
    id: UserId
